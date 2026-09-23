"""Decide deterministically; coverage thresholds never substitute for requirements."""

from .models import Applicability, ApplicabilityStatus, Finding, Severity

METADATA_GAPS = frozenset(
    {
        "ACC_MODALITY_UNKNOWN",
        "ACC_SPECIES_UNKNOWN",
        "ACC_TISSUE_UNKNOWN",
        "ACC_SAMPLE_TYPE_UNKNOWN",
        "ACC_ASSAY_UNKNOWN",
        "ACC_PLATFORM_UNKNOWN",
        "ACC_PREPROCESSING_UNKNOWN",
        "ACC_NORMALIZATION_UNKNOWN",
        "ACC_NORMALIZATION_REFERENCE_UNKNOWN",
        "ACC_PREPROCESSING_UNVERIFIED",
        "ACC_PREPROCESSING_UNBOUND",
        "ACC_UNIT_UNKNOWN",
        "ACC_GENOME_BUILD_UNKNOWN",
    }
)


def decide(findings: tuple[Finding, ...]) -> Applicability:
    blockers = tuple(f for f in findings if f.severity in {Severity.ERROR, Severity.BLOCKING})
    if any(
        f.code
        in {
            "ACC_IMPLEMENTATION_UNAVAILABLE",
            "ACC_MISSING_POLICY_UNSUPPORTED",
            "ACC_REQUIREMENT_UNRESOLVED",
        }
        for f in blockers
    ):
        status = ApplicabilityStatus.UNSUPPORTED
    elif any(f.code not in METADATA_GAPS for f in blockers):
        status = ApplicabilityStatus.NOT_APPLICABLE
    elif blockers:
        status = ApplicabilityStatus.INSUFFICIENT_METADATA
    else:
        status = ApplicabilityStatus.CONDITIONALLY_APPLICABLE
    return Applicability(
        status=status,
        can_compute=not blockers,
        reasons=blockers or tuple(f for f in findings if f.severity == Severity.WARNING),
        assumptions=(
            "Scientific metadata and normalization history are caller declarations, "
            "not independently verified processing evidence.",
        )
        if not blockers
        else (),
    )
