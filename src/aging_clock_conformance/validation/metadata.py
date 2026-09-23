"""Scientific compatibility checks driven by the registry, with no inferred metadata."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import ClockDefinition, Compatibility, Finding, Requirement, Sample, Severity

UNKNOWN_TOKENS = frozenset(
    {"unknown", "unresolved", "not documented", "not_documented", "n/a", "null"}
)


def is_unknown(value: str | None) -> bool:
    return value is None or not value.strip() or value.strip().lower() in UNKNOWN_TOKENS


@dataclass(frozen=True)
class CheckedMetadata:
    preprocessing: Compatibility
    assay_platform: Compatibility
    tissue: Compatibility
    findings: tuple[Finding, ...]


def check_metadata(clock: ClockDefinition, sample: Sample) -> CheckedMetadata:
    manifest = sample.manifest
    findings: list[Finding] = []

    def problem(code: str, message: str, severity: Severity = Severity.BLOCKING) -> None:
        findings.append(Finding(code=code, severity=severity, category="metadata", message=message))

    def requirement(name: str, value: str | None, spec: Requirement) -> Compatibility:
        if spec.status != "DOCUMENTED":
            problem(
                "ACC_REQUIREMENT_UNRESOLVED",
                f"Clock {name.lower()} requirements are unresolved or unsupported.",
            )
            return "UNSUPPORTED"
        if is_unknown(value):
            problem(f"ACC_{name}_UNKNOWN", f"Required {name.lower()} metadata is unavailable.")
            return "UNKNOWN"
        if value not in spec.accepted:
            problem(
                f"ACC_{name}_MISMATCH",
                f"Declared {name.lower()} is outside this clock profile's documented scope.",
            )
            return "INCOMPATIBLE"
        return "DECLARED_COMPATIBLE"

    if manifest and sample.sample_id != manifest.sample_id:
        problem("ACC_SAMPLE_MISMATCH", "Sample and manifest identifiers differ.")
    requirement("MODALITY", manifest.modality if manifest else None, clock.modality)
    requirement("SPECIES", manifest.species if manifest else None, clock.species)
    tissue = requirement("TISSUE", manifest.tissue if manifest else None, clock.tissue)
    requirement("SAMPLE_TYPE", manifest.sample_type if manifest else None, clock.sample_type)
    assay = requirement("ASSAY", manifest.assay.method if manifest else None, clock.assay)
    platform = requirement(
        "PLATFORM", manifest.assay.platform if manifest else None, clock.platform
    )
    priority: tuple[Compatibility, ...] = (
        "UNSUPPORTED",
        "INCOMPATIBLE",
        "UNKNOWN",
        "DECLARED_COMPATIBLE",
    )
    assay_platform = next(state for state in priority if state in (assay, platform))
    prep_states: list[Compatibility] = []
    prep = manifest.preprocessing if manifest else None
    for name, actual, expected in (
        ("PREPROCESSING", prep.stage if prep else None, clock.preprocessing.stage),
        ("NORMALIZATION", prep.normalization if prep else None, clock.preprocessing.normalization),
        (
            "NORMALIZATION_REFERENCE",
            prep.reference_sha256 if prep else None,
            clock.preprocessing.reference_sha256,
        ),
    ):
        if is_unknown(actual):
            problem(f"ACC_{name}_UNKNOWN", f"Required {name.lower()} provenance is unavailable.")
            prep_states.append("UNKNOWN")
        elif actual != expected:
            problem(
                f"ACC_{name}_MISMATCH", f"Declared {name.lower()} differs from the supported stage."
            )
            prep_states.append("INCOMPATIBLE")
        else:
            prep_states.append("DECLARED_COMPATIBLE")
    if not prep or is_unknown(prep.evidence):
        problem(
            "ACC_PREPROCESSING_UNVERIFIED",
            "A normalization provenance record must be supplied; "
            "a method name alone is insufficient.",
        )
        prep_states.append("UNKNOWN")
    if not manifest or not manifest.measurements_sha256:
        problem(
            "ACC_PREPROCESSING_UNBOUND",
            "Manifest must bind preprocessing provenance to the input checksum.",
        )
        prep_states.append("UNKNOWN")
    preprocessing = next(state for state in priority if state in prep_states)
    if not manifest or not manifest.unit:
        if not sample.measurements or any(row.unit is None for row in sample.measurements):
            problem(
                "ACC_UNIT_UNKNOWN", "Declare units in the manifest or in every measurement row."
            )
    elif manifest.unit != clock.feature_contract.unit:
        problem("ACC_UNIT_MISMATCH", "Declared sample unit differs from the clock contract.")
    if not manifest or is_unknown(manifest.genome_build):
        problem(
            "ACC_GENOME_BUILD_UNKNOWN",
            clock.genome_build_note,
            Severity.BLOCKING if clock.genome_build_required else Severity.INFO,
        )
    if preprocessing == "DECLARED_COMPATIBLE":
        problem(
            "ACC_PREPROCESSING_DECLARED",
            "Normalization history is caller-declared; "
            "this tool has not independently audited the processing run.",
            Severity.WARNING,
        )
    return CheckedMetadata(preprocessing, assay_platform, tissue, tuple(findings))
