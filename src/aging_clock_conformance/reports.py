"""Canonical report envelopes with a stable content-derived run identifier."""

from __future__ import annotations

from .models import (
    ComparisonReport,
    ConformanceReport,
    ImplementationMetadata,
    RunReport,
    Sample,
    ScoreResult,
    ValidationReport,
)
from .provenance import get_provenance
from .registry import Clock
from .serialization import canonical_json, sha256_bytes


def make_report(
    operation: str,
    clock: Clock,
    *,
    sample: Sample | None = None,
    validation: ValidationReport | None = None,
    implementation: ImplementationMetadata | None = None,
    result: ScoreResult | None = None,
    conformance: ConformanceReport | None = None,
    comparison: ComparisonReport | None = None,
) -> RunReport:
    report = RunReport(
        run_id="0" * 64,
        operation=operation,
        clock=clock.definition,
        input_validation=validation,
        implementation=implementation,
        result=result,
        conformance=conformance,
        comparison=comparison,
        provenance=get_provenance(clock, sample),
    )
    content = report.model_dump(mode="json", exclude={"run_id"})
    del content["provenance"]["execution_timestamp"]
    return report.model_copy(update={"run_id": sha256_bytes(canonical_json(content).encode())})


def report_markdown(report: RunReport) -> str:
    lines = [
        f"# {report.clock.name}",
        "",
        f"Operation: `{report.operation}`",
        "",
        f"Run ID: `{report.run_id}`",
        "",
    ]
    if report.input_validation:
        v = report.input_validation
        lines.extend(
            [
                f"Applicability: **{v.applicability.status}**",
                "",
                f"Usable features: {v.coverage.valid_numeric_count}/{v.coverage.required_count}",
                "",
            ]
        )
        if v.applicability.reasons:
            lines.extend(
                f"- `{finding.code}`: {finding.message}" for finding in v.applicability.reasons
            )
            lines.append("")
    if report.result:
        lines.extend([f"Result: {report.result.value:.12g} {report.result.unit}", ""])
    if report.conformance:
        c = report.conformance
        lines.extend(
            [
                f"Conformance: **{c.status}**, {c.passed} passed, {c.failed} failed ({c.profile}).",
                "",
            ]
        )
    if report.comparison:
        lines.extend([f"Comparison passed: {report.comparison.passed}", ""])
    lines.extend(
        [
            f"Project version: {report.provenance.project_version}",
            "",
            f"Executed: {report.provenance.execution_timestamp}",
            "",
            "Research measurements only. Computational conformance does not establish "
            "population or clinical validity.",
            "",
        ]
    )
    return "\n".join(lines)
