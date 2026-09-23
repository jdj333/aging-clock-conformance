import asyncio
import json
import sys
from datetime import timedelta

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from aging_clock_conformance import inline_sample, validate_sample
from aging_clock_conformance.mcp.server import create_server

pytestmark = pytest.mark.mcp


def structured(result):
    if isinstance(result, tuple):
        return result[1]
    if isinstance(result, dict):
        return result
    return json.loads(result[0].text)


def test_discovery_exposes_only_read_only_tools():
    tools = asyncio.run(create_server().list_tools())
    assert {tool.name for tool in tools} == {
        "list_clocks",
        "get_clock",
        "get_clock_requirements",
        "validate_clock_input",
        "check_clock_applicability",
        "get_feature_coverage",
        "run_conformance",
        "get_conformance_status",
        "compare_implementations",
        "get_clock_provenance",
    }
    for tool in tools:
        assert tool.annotations.readOnlyHint and not tool.annotations.openWorldHint
        assert not (
            {"path", "file", "command", "root"} & set(tool.inputSchema.get("properties", {}))
        )


@pytest.mark.parametrize(
    "tool_name,section",
    [
        ("validate_clock_input", None),
        ("check_clock_applicability", "applicability"),
        ("get_feature_coverage", "coverage"),
    ],
)
def test_mcp_matches_core_for_bad_inputs(clock, sample, tool_name, section):
    rows = [row.model_dump(mode="json") for row in sample.measurements[:3]]
    rows.append(rows[0])
    rows[1]["value"] = "NaN"
    from aging_clock_conformance.models import Measurement

    core = validate_sample(
        clock=clock, sample=inline_sample(tuple(Measurement.model_validate(row) for row in rows))
    ).model_dump(mode="json")
    output = structured(
        asyncio.run(
            create_server().call_tool(tool_name, {"clock_id": "horvath-2013", "measurements": rows})
        )
    )
    assert output == core if section is None else output[section] == core[section]
    assert not (output if section is None else core)["applicability"]["can_compute"]


@pytest.mark.parametrize("tool_name", ["run_conformance", "get_conformance_status"])
def test_mcp_fresh_conformance(tool_name):
    result = structured(
        asyncio.run(create_server().call_tool(tool_name, {"clock_id": "horvath-2013"}))
    )
    assert result["conformance"]["passed"] == 16
    assert result["conformance"]["profile"] == "score-v1"
    assert result["result"] is None


def test_unknown_clock_returns_stable_error():
    output = structured(
        asyncio.run(create_server().call_tool("get_clock", {"clock_id": "unknown"}))
    )
    assert output["error"]["code"] == "ACC_UNKNOWN_CLOCK"


def test_mcp_local_file_reference_is_rejected(sample):
    metadata = sample.manifest.model_copy(update={"measurements": "/etc/passwd"}).model_dump(
        mode="json"
    )
    result = structured(
        asyncio.run(
            create_server().call_tool(
                "validate_clock_input",
                {
                    "clock_id": "horvath-2013",
                    "measurements": [],
                    "metadata": metadata,
                },
            )
        )
    )
    assert result["error"]["code"] == "ACC_INLINE_PATH_FORBIDDEN"


def test_stdio_protocol_round_trip():
    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "aging_clock_conformance.mcp.server"]
        )
        async with (
            stdio_client(parameters) as (reader, writer),
            ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=20)) as session,
        ):
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "Aging Clock Conformance"
            tools = await session.list_tools()
            assert len(tools.tools) == 10
            result = await session.call_tool("get_clock_requirements", {"clock_id": "horvath-2013"})
            assert not result.isError
            assert len(result.structuredContent["features"]) == 353
            blocked = await session.call_tool(
                "check_clock_applicability",
                {
                    "clock_id": "horvath-2013",
                    "measurements": [],
                },
            )
            assert not blocked.structuredContent["applicability"]["can_compute"]

    asyncio.run(exercise())
