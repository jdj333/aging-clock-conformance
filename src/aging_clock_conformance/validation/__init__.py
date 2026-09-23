"""Shared validation entry point used before every adapter computation."""

from __future__ import annotations

from ..applicability import decide
from ..coverage import feature_coverage
from ..models import Dimensions, Finding, Sample, Severity, ValidationReport
from ..registry import Clock
from .metadata import check_metadata
from .values import check_values


def validate(
    clock: Clock, sample: Sample, *, implementation_available: bool = True
) -> ValidationReport:
    definition = clock.definition
    checked = check_values(
        sample.measurements,
        definition.feature_contract,
        sample.manifest.unit if sample.manifest else None,
    )
    coverage = feature_coverage(clock.required_features, checked)
    metadata = check_metadata(definition, sample)
    findings = [*sample.input_findings, *checked.findings, *metadata.findings]
    if coverage.missing_count:
        findings.append(
            Finding(
                code="ACC_MISSING_FEATURES",
                severity=Severity.BLOCKING,
                category="coverage",
                message=f"{coverage.missing_count} required features are absent; "
                "this profile does not impute.",
            )
        )
    if coverage.extra_count:
        findings.append(
            Finding(
                code="ACC_EXTRA_FEATURES",
                severity=Severity.INFO,
                category="coverage",
                message=f"{coverage.extra_count} additional features are excluded from the score.",
            )
        )
    if definition.missing_data.policy != "complete_required":
        findings.append(
            Finding(
                code="ACC_MISSING_POLICY_UNSUPPORTED",
                severity=Severity.BLOCKING,
                category="implementation",
                message="This engine cannot execute the clock's missing-data policy.",
            )
        )
    if not implementation_available:
        findings.append(
            Finding(
                code="ACC_IMPLEMENTATION_UNAVAILABLE",
                severity=Severity.BLOCKING,
                category="implementation",
                message="No compatible execution adapter is available.",
            )
        )
    ordered = tuple(
        sorted(findings, key=lambda f: (f.category, f.code, f.feature_id or "", f.row or 0))
    )
    applicability = decide(ordered)
    dimensions = Dimensions(
        schema_validity="INVALID"
        if any(
            f.category == "schema" and f.severity in {Severity.ERROR, Severity.BLOCKING}
            for f in ordered
        )
        else "VALID",
        input_data_quality="FAIL"
        if any(
            f.category == "data_quality" and f.severity in {Severity.ERROR, Severity.BLOCKING}
            for f in ordered
        )
        else "PASS",
        feature_coverage="COMPLETE"
        if coverage.valid_numeric_count == coverage.required_count
        else "INCOMPLETE",
        preprocessing_compatibility=metadata.preprocessing,
        assay_platform_compatibility=metadata.assay_platform,
        tissue_compatibility=metadata.tissue,
        computational_applicability=applicability.status,
        reference_conformance="NOT_RUN",
    )
    return ValidationReport(
        clock_id=definition.clock_id,
        sample_id=sample.sample_id,
        input_sha256=sample.input_sha256,
        manifest_sha256=sample.manifest_sha256,
        dimensions=dimensions,
        findings=ordered,
        coverage=coverage,
        applicability=applicability,
    )
