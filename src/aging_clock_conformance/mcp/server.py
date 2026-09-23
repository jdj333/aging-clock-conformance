"""Local stdio tools over the core API, without filesystem parameters or scoring."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, ParamSpec

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from ..api import comparison_report, conformance_report, validate_sample
from ..errors import ACCError
from ..inputs import inline_sample
from ..models import Measurement, SampleManifest
from ..provenance import get_provenance
from ..registry import Registry

P = ParamSpec("P")
Rows = Annotated[list[Measurement], Field(max_length=100_000)]
READ_ONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


def structured_errors(function: Callable[P, dict[str, Any]]) -> Callable[P, dict[str, Any]]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> dict[str, Any]:
        try:
            return function(*args, **kwargs)
        except ACCError as error:
            return {"status": "error", "error": {"code": error.code, "message": str(error)}}

    return wrapped


def create_server(registry: Registry | None = None) -> FastMCP:
    registry = registry or Registry.load_default()
    server = FastMCP(
        "Aging Clock Conformance",
        instructions=(
            "Research infrastructure. Coverage, applicability, computational conformance, "
            "population validity, and clinical validity are separate. Never infer normalization "
            "or impute. Input is inline only; no tools read arbitrary local files or execute "
            "user commands. No scoring tool is exposed."
        ),
    )

    @server.tool(annotations=READ_ONLY)
    @structured_errors
    def list_clocks() -> dict[str, Any]:
        """List actual registered clocks and their supported stages."""
        return {
            "clocks": [
                {
                    "clock_id": c.definition.clock_id,
                    "name": c.definition.name,
                    "version": c.definition.version,
                    "stage": c.definition.preprocessing.stage,
                }
                for c in registry.list()
            ]
        }

    @server.tool(annotations=READ_ONLY)
    @structured_errors
    def get_clock(clock_id: str) -> dict[str, Any]:
        """Return the complete source-backed clock definition."""
        return registry.get(clock_id).definition.model_dump(mode="json")

    @server.tool(annotations=READ_ONLY)
    @structured_errors
    def get_clock_requirements(clock_id: str) -> dict[str, Any]:
        """Return scientific input requirements, required feature IDs, and scope limits."""
        clock = registry.get(clock_id)
        definition = clock.definition.model_dump(mode="json")
        keys = (
            "modality",
            "species",
            "tissue",
            "sample_type",
            "assay",
            "platform",
            "feature_contract",
            "preprocessing",
            "missing_data",
            "genome_build_required",
            "genome_build_note",
        )
        return {
            "clock_id": clock.definition.clock_id,
            "requirements": {key: definition[key] for key in keys},
            "features": list(clock.required_features),
        }

    def validation(
        clock_id: str, measurements: list[Measurement], metadata: SampleManifest | None
    ) -> dict[str, Any]:
        return validate_sample(
            clock=registry.get(clock_id), sample=inline_sample(tuple(measurements), metadata)
        ).model_dump(mode="json")

    @server.tool(annotations=READ_ONLY)
    @structured_errors
    def validate_clock_input(
        clock_id: str, measurements: Rows, metadata: SampleManifest | None = None
    ) -> dict[str, Any]:
        """Validate inline measurements. Invalid input returns structured blocking reasons."""
        return validation(clock_id, measurements, metadata)

    @server.tool(annotations=READ_ONLY)
    @structured_errors
    def check_clock_applicability(
        clock_id: str, measurements: Rows, metadata: SampleManifest | None = None
    ) -> dict[str, Any]:
        """Decide applicability with the same scientific gates as the Python API and CLI."""
        return {
            "clock_id": clock_id,
            "applicability": validation(clock_id, measurements, metadata)["applicability"],
        }

    @server.tool(annotations=READ_ONLY)
    @structured_errors
    def get_feature_coverage(
        clock_id: str, measurements: Rows, metadata: SampleManifest | None = None
    ) -> dict[str, Any]:
        """Return coverage without treating coverage as scoring permission."""
        report = validation(clock_id, measurements, metadata)
        return {
            "clock_id": clock_id,
            "coverage": report["coverage"],
            "applicability": report["applicability"],
        }

    @server.tool(name="run_conformance", annotations=READ_ONLY)
    @structured_errors
    def run_conformance_tool(clock_id: str, implementation: str = "python-fsum") -> dict[str, Any]:
        """Execute the public conformance fixture, with exact inputs and provenance."""
        return conformance_report(registry.get(clock_id), implementation).model_dump(mode="json")

    @server.tool(annotations=READ_ONLY)
    @structured_errors
    def get_conformance_status(
        clock_id: str, implementation: str = "python-fsum"
    ) -> dict[str, Any]:
        """Return a freshly executed conformance report, never an inherited status flag."""
        return conformance_report(registry.get(clock_id), implementation).model_dump(mode="json")

    @server.tool(name="compare_implementations", annotations=READ_ONLY)
    @structured_errors
    def compare_tool(clock_id: str, implementations: list[str] | None = None) -> dict[str, Any]:
        """Compare executed score implementations and independently recorded reference outputs."""
        ids = (
            tuple(implementations)
            if implementations is not None
            else ("python-fsum", "python-decimal")
        )
        return comparison_report(registry.get(clock_id), ids).model_dump(mode="json")

    @server.tool(annotations=READ_ONLY)
    @structured_errors
    def get_clock_provenance(clock_id: str) -> dict[str, Any]:
        """Return publication, version, checksums, and local runtime provenance."""
        return get_provenance(registry.get(clock_id)).model_dump(mode="json")

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
