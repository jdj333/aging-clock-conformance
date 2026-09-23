"""Application functions used unchanged by the CLI and MCP tools."""

from __future__ import annotations

from pathlib import Path

from .adapters import adapter_available, get_adapter
from .applicability import decide
from .conformance import compare_implementations, run_conformance
from .errors import ACCError
from .inputs import InputFormat, load_sample
from .models import Finding, RunReport, Sample, SampleManifest, Severity, ValidationReport
from .registry import Clock
from .reports import make_report
from .validation import validate


def _sample(
    sample: str | Path | Sample,
    manifest: str | Path | SampleManifest | None,
    sample_id: str | None,
    input_format: InputFormat | None,
) -> Sample:
    if isinstance(sample, Sample):
        if manifest is not None or sample_id is not None or input_format is not None:
            raise ACCError(
                "ACC_INPUT_CONFIG",
                "An in-memory Sample already contains its metadata and selection.",
            )
        return sample
    return load_sample(sample, manifest=manifest, sample_id=sample_id, input_format=input_format)


def validate_sample(
    *,
    clock: Clock,
    sample: str | Path | Sample,
    manifest: str | Path | SampleManifest | None = None,
    sample_id: str | None = None,
    input_format: InputFormat | None = None,
) -> ValidationReport:
    loaded = _sample(sample, manifest, sample_id, input_format)
    return validate(clock, loaded, implementation_available=adapter_available(clock))


def inspect_sample(
    *,
    clock: Clock,
    sample: str | Path | Sample,
    manifest: str | Path | SampleManifest | None = None,
    sample_id: str | None = None,
    input_format: InputFormat | None = None,
    operation: str = "validate",
) -> RunReport:
    if operation not in {"validate", "coverage", "applicability"}:
        raise ACCError("ACC_UNKNOWN_OPERATION", "Unsupported validation report operation.")
    loaded = _sample(sample, manifest, sample_id, input_format)
    validation = validate_sample(clock=clock, sample=loaded)
    return make_report(operation, clock, sample=loaded, validation=validation)


def score_sample(
    *,
    clock: Clock,
    sample: str | Path | Sample,
    manifest: str | Path | SampleManifest | None = None,
    sample_id: str | None = None,
    input_format: InputFormat | None = None,
    implementation: str = "python-fsum",
) -> RunReport:
    loaded = _sample(sample, manifest, sample_id, input_format)
    adapter = get_adapter(clock, implementation)
    validation = validate_sample(clock=clock, sample=loaded)
    if not validation.applicability.can_compute:
        return make_report(
            "score", clock, sample=loaded, validation=validation, implementation=adapter.metadata()
        )
    conformance = run_conformance(clock, adapter)
    dimensions = validation.dimensions.model_copy(
        update={"reference_conformance": conformance.status}
    )
    validation = validation.model_copy(update={"dimensions": dimensions})
    result = None
    if conformance.status == "REFERENCE_CONFORMANT":
        result = adapter.score(clock, loaded)
    else:
        finding = Finding(
            code="ACC_REFERENCE_NONCONFORMANT",
            severity=Severity.BLOCKING,
            category="implementation",
            message="Execution adapter failed the current reference conformance run.",
        )
        findings = (*validation.findings, finding)
        applicability = decide(findings)
        validation = validation.model_copy(
            update={
                "findings": findings,
                "applicability": applicability,
                "dimensions": dimensions.model_copy(
                    update={"computational_applicability": applicability.status}
                ),
            }
        )
    return make_report(
        "score",
        clock,
        sample=loaded,
        validation=validation,
        implementation=adapter.metadata(),
        result=result,
        conformance=conformance,
    )


def conformance_report(clock: Clock, implementation: str = "python-fsum") -> RunReport:
    result = run_conformance(clock, implementation)
    return make_report(
        "conformance", clock, implementation=result.implementation, conformance=result
    )


def comparison_report(
    clock: Clock, implementations: tuple[str, ...] = ("python-fsum", "python-decimal")
) -> RunReport:
    return make_report("compare", clock, comparison=compare_implementations(clock, implementations))
