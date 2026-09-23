"""Terminal presentation over the public application API; no scientific logic."""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

import typer
from pydantic import ValidationError
from rich.console import Console

from .api import comparison_report, conformance_report, inspect_sample, score_sample
from .conformance import load_fixture
from .errors import ACCError
from .inputs import InputFormat
from .models import RunReport
from .provenance import PROJECT_VERSION, get_provenance
from .registry import Registry
from .reports import report_markdown
from .serialization import canonical_json

app = typer.Typer(
    help="Validate biological clock inputs and test reference conformance.", no_args_is_help=True
)
conformance_app = typer.Typer(
    help="Inspect and execute immutable reference fixtures.", no_args_is_help=True
)
registry_app = typer.Typer(help="Inspect registry and artifact integrity.", no_args_is_help=True)
app.add_typer(conformance_app, name="conformance")
app.add_typer(registry_app, name="registry")
P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True)
class Options:
    quiet: bool = False
    verbose: bool = False


OPTIONS: ContextVar[Options] = ContextVar("cli_options")


@app.callback()
def global_options(
    ctx: typer.Context,
    quiet: bool = typer.Option(False, "--quiet", help="Suppress human output; preserve JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Include all validation findings."),
) -> None:
    if quiet and verbose:
        raise typer.BadParameter("--quiet and --verbose are mutually exclusive")
    ctx.obj = Options(quiet, verbose)
    OPTIONS.set(ctx.obj)


def boundary(function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return function(*args, **kwargs)
        except (ACCError, ValidationError, OSError) as error:
            code = (
                error.code
                if isinstance(error, ACCError)
                else "ACC_INVALID_CONFIG"
                if isinstance(error, ValidationError)
                else "ACC_IO_ERROR"
            )
            message = (
                str(error)
                if isinstance(error, ACCError)
                else "Configuration or local file operation failed."
            )
            if kwargs.get("json_output"):
                typer.echo(
                    canonical_json(
                        {
                            "schema_version": "1.0",
                            "status": "error",
                            "error": {"code": code, "message": message},
                        }
                    ),
                    nl=False,
                )
            else:
                typer.echo(f"{code}: {message}", err=True)
            raise typer.Exit(2) from error

    return guarded


def emit(value: Any, *, json_output: bool, summary: list[str], markdown: bool = False) -> None:
    if json_output and markdown:
        raise ACCError("ACC_OUTPUT_CONFIG", "Choose JSON or Markdown, not both.")
    if json_output:
        typer.echo(canonical_json(value), nl=False)
    elif markdown:
        if not isinstance(value, RunReport):
            raise ACCError("ACC_OUTPUT_CONFIG", "Markdown output requires an execution report.")
        typer.echo(report_markdown(value), nl=False)
    elif not OPTIONS.get().quiet:
        console = Console(highlight=False)
        for line in summary:
            console.print(line, markup=False)


@app.command("version")
@boundary
def version_command(json_output: bool = typer.Option(False, "--json")) -> None:
    emit(
        {"version": PROJECT_VERSION},
        json_output=json_output,
        summary=[f"aging-clock {PROJECT_VERSION}"],
    )


@app.command("list")
@boundary
def list_command(json_output: bool = typer.Option(False, "--json")) -> None:
    clocks = Registry.load_default().list()
    values = [
        {
            "clock_id": c.definition.clock_id,
            "name": c.definition.name,
            "version": c.definition.version,
            "stage": c.definition.preprocessing.stage,
            "implementations": c.definition.implementation_ids,
        }
        for c in clocks
    ]
    emit(
        values,
        json_output=json_output,
        summary=[
            f"{c.definition.clock_id}  {c.definition.name}  ({c.definition.preprocessing.stage})"
            for c in clocks
        ],
    )


@app.command("show")
@boundary
def show_command(clock: str, json_output: bool = typer.Option(False, "--json")) -> None:
    definition = Registry.load_default().get(clock).definition
    emit(
        definition,
        json_output=json_output,
        summary=[
            f"{definition.name} ({definition.version})",
            f"Stage: {definition.preprocessing.stage}",
            f"Required features: {definition.feature_contract.count}; "
            f"policy: {definition.missing_data.policy}",
            f"Normalization: {definition.preprocessing.normalization}",
            f"Tissues: {', '.join(definition.tissue.accepted)}",
            f"Platforms: {', '.join(definition.platform.accepted)}",
            f"Implementations: {', '.join(definition.implementation_ids)}",
            "Normalization declarations permit conditional computation only. "
            "See --json for sources and the complete contract.",
        ],
    )


def _validation_command(
    operation: str,
    input_path: Path,
    clock_id: str,
    manifest: Path | None,
    sample_id: str | None,
    input_format: InputFormat | None,
    json_output: bool,
    markdown: bool,
    implementation: str = "python-fsum",
) -> None:
    clock = Registry.load_default().get(clock_id)
    if operation == "score":
        report = score_sample(
            clock=clock,
            sample=input_path,
            manifest=manifest,
            sample_id=sample_id,
            input_format=input_format,
            implementation=implementation,
        )
    else:
        report = inspect_sample(
            clock=clock,
            sample=input_path,
            manifest=manifest,
            sample_id=sample_id,
            input_format=input_format,
            operation=operation,
        )
    validation = report.input_validation
    assert validation is not None
    coverage = validation.coverage
    summary = [
        f"Clock: {clock.definition.name}",
        f"Sample: {validation.sample_id}",
        f"Applicability: {validation.applicability.status}; "
        f"can compute: {validation.applicability.can_compute}",
        f"Coverage: {coverage.present_count}/{coverage.required_count} present "
        f"({coverage.coverage_percentage:.2f}%)",
        f"Usable: {coverage.valid_numeric_count}/{coverage.required_count} "
        f"({coverage.usable_coverage_percentage:.2f}%); missing: {coverage.missing_count}; "
        f"invalid: {coverage.invalid_count}; extra: {coverage.extra_count}",
    ]
    if report.result:
        summary.append(
            f"Result: {report.result.value:.12g} {report.result.unit}; "
            f"linear score: {report.result.linear_score:.16g}"
        )
    findings = (
        validation.findings if OPTIONS.get().verbose else validation.applicability.reasons[:8]
    )
    summary.extend(f"{finding.severity} {finding.code}: {finding.message}" for finding in findings)
    if len(validation.applicability.reasons) > len(findings):
        summary.append("Additional reasons are available with --verbose or --json.")
    emit(report, json_output=json_output, markdown=markdown, summary=summary)
    if operation != "coverage" and (
        not validation.applicability.can_compute or (operation == "score" and report.result is None)
    ):
        raise typer.Exit(1)


@app.command("validate")
@boundary
def validate_command(
    input_path: Path,
    clock: str = typer.Option(..., "--clock"),
    manifest: Path | None = None,
    sample_id: str | None = typer.Option(None, "--sample"),
    input_format: InputFormat | None = typer.Option(None, "--format"),
    json_output: bool = typer.Option(False, "--json"),
    markdown: bool = False,
) -> None:
    _validation_command(
        "validate", input_path, clock, manifest, sample_id, input_format, json_output, markdown
    )


@app.command("coverage")
@boundary
def coverage_command(
    input_path: Path,
    clock: str = typer.Option(..., "--clock"),
    manifest: Path | None = None,
    sample_id: str | None = typer.Option(None, "--sample"),
    input_format: InputFormat | None = typer.Option(None, "--format"),
    json_output: bool = typer.Option(False, "--json"),
    markdown: bool = False,
) -> None:
    _validation_command(
        "coverage", input_path, clock, manifest, sample_id, input_format, json_output, markdown
    )


@app.command("applicability")
@boundary
def applicability_command(
    input_path: Path,
    clock: str = typer.Option(..., "--clock"),
    manifest: Path | None = None,
    sample_id: str | None = typer.Option(None, "--sample"),
    input_format: InputFormat | None = typer.Option(None, "--format"),
    json_output: bool = typer.Option(False, "--json"),
    markdown: bool = False,
) -> None:
    _validation_command(
        "applicability", input_path, clock, manifest, sample_id, input_format, json_output, markdown
    )


@app.command("score")
@boundary
def score_command(
    input_path: Path,
    clock: str = typer.Option(..., "--clock"),
    manifest: Path | None = None,
    sample_id: str | None = typer.Option(None, "--sample"),
    input_format: InputFormat | None = typer.Option(None, "--format"),
    implementation: str = "python-fsum",
    json_output: bool = typer.Option(False, "--json"),
    markdown: bool = False,
) -> None:
    _validation_command(
        "score",
        input_path,
        clock,
        manifest,
        sample_id,
        input_format,
        json_output,
        markdown,
        implementation,
    )


@conformance_app.command("list")
@boundary
def conformance_list(json_output: bool = typer.Option(False, "--json")) -> None:
    suites = [load_fixture(c).suite for c in Registry.load_default().list()]
    emit(
        [s.model_dump(mode="json") for s in suites],
        json_output=json_output,
        summary=[
            f"{s.clock_id}: {s.fixture_id} v{s.version}, {len(s.samples)} samples, {s.profile}"
            for s in suites
        ],
    )


@conformance_app.command("run")
@boundary
def conformance_run(
    clock: str,
    implementation: str = "python-fsum",
    json_output: bool = typer.Option(False, "--json"),
    markdown: bool = False,
) -> None:
    report = conformance_report(Registry.load_default().get(clock), implementation)
    result = report.conformance
    assert result is not None
    emit(
        report,
        json_output=json_output,
        markdown=markdown,
        summary=[
            f"Clock: {report.clock.name}",
            f"Implementation: {result.implementation.implementation_id}",
            f"Profile: {result.profile} ({result.implementation.stage.replace('_', ' ')} scoring)",
            f"Samples: {len(result.cases)}; passed: {result.passed}; failed: {result.failed}",
            f"Tolerance: score {result.tolerance.linear_score_absolute:g}; "
            f"result {result.tolerance.result_absolute:g} {report.clock.result_unit}",
            f"Status: {result.status}",
            f"Reference: {result.reference_implementation.implementation_id} "
            f"({result.reference_implementation.execution_mode}); "
            f"{result.reference_implementation.runtime}",
        ],
    )
    if result.failed:
        raise typer.Exit(1)


@app.command("compare")
@boundary
def compare_command(
    clock: str = typer.Option(..., "--clock"),
    implementation: list[str] | None = typer.Option(None, "--implementation"),
    json_output: bool = typer.Option(False, "--json"),
    markdown: bool = False,
) -> None:
    report = comparison_report(
        Registry.load_default().get(clock),
        tuple(implementation) if implementation else ("python-fsum", "python-decimal"),
    )
    result = report.comparison
    assert result is not None
    summary = [
        f"Comparison: {result.profile}; passed: {result.passed}",
        "Sample         Expected          "
        + "  ".join(r.implementation.implementation_id for r in result.runs)
        + "  Max difference  Pass",
    ]
    for case in result.cases:
        observed = "  ".join(
            f"{value.value:.12g}" if value else "blocked" for value in case.results.values()
        )
        summary.append(
            f"{case.sample_id}  {case.expected.value:.12g}  {observed}  "
            f"{case.absolute_difference}  {case.passed}"
        )
    summary.append(
        "Each executed implementation is independently checked against the recorded R fixture."
    )
    emit(report, json_output=json_output, markdown=markdown, summary=summary)
    if not result.passed:
        raise typer.Exit(1)


@app.command("provenance")
@boundary
def provenance_command(clock: str, json_output: bool = typer.Option(False, "--json")) -> None:
    provenance = get_provenance(Registry.load_default().get(clock))
    emit(
        provenance,
        json_output=json_output,
        summary=[
            f"Project: {provenance.project_version}; "
            f"commit: {provenance.git_commit or 'unavailable'}; dirty: {provenance.git_dirty}",
            f"Definition SHA-256: {provenance.clock_definition_sha256}",
            f"Verified reference artifacts: {len(provenance.reference_checksums)}",
            *[f"{source.id}: {source.url}" for source in provenance.sources],
        ],
    )


@registry_app.command("validate")
@boundary
def registry_validate(json_output: bool = typer.Option(False, "--json")) -> None:
    registry = Registry.load_default()
    clocks = registry.list()
    for clock in clocks:
        load_fixture(clock)
    files = registry.verify_integrity()
    emit(
        {"valid": True, "clocks": len(clocks), "artifacts": len(files)},
        json_output=json_output,
        summary=[
            f"Registry valid: {len(clocks)} clock(s), {len(files)} checksummed artifacts, "
            "fixture schemas validated."
        ],
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
