# MCP: thin, local agent access

Install the optional transport from the checkout:

```sh
python -m pip install '.[mcp]'
aging-clock-mcp
```

The process speaks MCP on stdin/stdout using the official Python SDK. A client
starts it as a child process; it does not print an interactive prompt. Use the
absolute executable path from your installed virtual environment. There is no API
key, remote listener, scoring tool, or proprietary LLM dependency.

## Codex

From the repository root after the development install:

```sh
codex mcp add aging-clock -- "$PWD/.venv/bin/aging-clock-mcp"
codex mcp list
```

Alternatively, put an explicit path in your Codex configuration:

```toml
[mcp_servers.aging-clock]
command = "/absolute/path/to/aging-clock-conformance/.venv/bin/aging-clock-mcp"
```

The stdio registration syntax was checked against the installed Codex CLI help and
[official OpenAI MCP documentation](https://developers.openai.com/codex/mcp).
These commands are setup instructions; this repository does not modify your client
configuration automatically.

## Claude Code

```sh
claude mcp add --transport stdio aging-clock -- "$PWD/.venv/bin/aging-clock-mcp"
claude mcp list
```

The `--` delimiter separates client options from the server executable, as described
in [Claude Code's MCP documentation](https://code.claude.com/docs/en/mcp).

## Other stdio clients

Clients that use an `mcpServers` JSON configuration can adapt:

```json
{
  "mcpServers": {
    "aging-clock": {
      "command": "/absolute/path/to/.venv/bin/aging-clock-mcp",
      "args": []
    }
  }
}
```

## Tool contract

| Tool | Result |
| --- | --- |
| `list_clocks` | Actual registry entries and supported stage |
| `get_clock` | Complete source-backed definition |
| `get_clock_requirements` | Metadata requirements and all required feature identifiers |
| `validate_clock_input` | Core `ValidationReport` including input digest, dimensions and findings |
| `check_clock_applicability` | Core applicability decision with structured reasons |
| `get_feature_coverage` | Core coverage plus a separate applicability decision |
| `run_conformance` | Full report from a fresh public fixture run |
| `get_conformance_status` | Fresh report, never a cached or inherited upstream flag |
| `compare_implementations` | Executed paths versus each other and recorded reference evidence |
| `get_clock_provenance` | Source, artifact, version, checksum and runtime evidence |

Validation tools accept `clock_id`, `measurements` (a list of Measurement objects),
and optional `metadata` (a SampleManifest). No tool accepts a filesystem root,
input filename, code, or command. A non-null `metadata.measurements` path is rejected.
Inline checksums use the [canonical inline contract](input-format.md); a CSV digest
cannot substitute for the digest of differently serialized inline rows. Requests are
limited to 100,000 measurement rows per validation call.

Example arguments that should be rejected scientifically:

```json
{
  "clock_id": "horvath-2013",
  "measurements": [],
  "metadata": null
}
```

The applicability is blocked, with empty input, missing-feature and missing-metadata
codes. A malformed request is a protocol/schema error; application errors return
`status: error` and a stable `error.code`. Expected scientific abstention is a normal
structured tool result, not an invented age or exception traceback.

Tests exercise discovery, read-only annotations, semantic equality with the core,
path rejection, and an actual stdio initialize/list/call exchange. Use
`pytest -m mcp` to run them. A hosted client may retain inputs/results according to
its own policy; local server behavior does not determine the client's privacy model.
