# Architecture

The package has one deterministic application layer and two transports. Neither
transport implements scientific arithmetic or a second applicability policy.

| Module | Responsibility |
| --- | --- |
| `models.py` | Frozen typed contracts; the source of generated JSON Schemas |
| `registry.py` | Verified packaged assets, source references, unique coefficient IDs, intercept consistency |
| `inputs.py` | Explicit long/matrix CSV, sample selection, manifests, inline samples, raw-byte digests |
| `validation/values.py` | Preserve rows, parse values, reject duplicates and invalid measurements |
| `validation/metadata.py` | Compare explicit metadata with source-backed requirements |
| `coverage.py` | Required/present/usable/missing/invalid/extra counts and sets |
| `applicability.py` | Deterministic decision and structured reasons |
| `adapters/` | Clock-specific formulas and implementation metadata behind `ClockAdapter` |
| `conformance/` | Immutable fixture loading, independent expectations, tolerance checks and comparison |
| `provenance.py`, `reports.py` | Checksums, source/runtime evidence, stable JSON envelopes and Markdown |
| `api.py` | Shared validate/inspect/score/conformance/compare services |
| `cli.py`, `mcp/` | Presentation and transport only |

## Storage and distribution

`src/aging_clock_conformance/data/` is the single canonical registry location. Its
JSON, CSV, source artifacts, and integrity manifest ship in the wheel and source
archive. There is no second root-level registry copy, database, or network lookup.
Paths in artifacts are relative to this data root; path traversal and escaping
symlinks are rejected. Registry discovery verifies every packaged artifact.

Immutable tuples hold coefficients, sources, requirements, findings, and rows.
The only feature lookup dictionary used by an adapter is constructed **after**
validation has rejected duplicates. Scientific state is not a mutable module global.

## Execution boundaries

`validate_sample` returns a `ValidationReport`; `inspect_sample` adds a provenance
envelope. Public `score_sample` first validates the sample, then runs fresh reference
conformance for the chosen adapter, and computes only if both gates pass. The
adapter repeats the input checks and verifies coefficient integrity, protecting
direct API calls. Conformance uses this same guarded adapter with the public fixture.
It does not recursively invoke the public scoring service.

Custom adapters implement `ClockAdapter.metadata()` and `score(clock, sample)`.
`run_conformance` and `compare_implementations` accept protocol implementations,
including test adapters; production discovery is an explicit allowlist. Arbitrary
Python imports, shell commands, or dynamically downloaded plugins are not accepted
from input manifests or MCP requests.

## Generalization limits

The first executable profile is a weighted numeric predictor with a linear score
and a scalar result. The registry permits different modalities, identifiers, units,
and bounds. A nonlinear or multi-output model may require a new result schema and
adapter profile. Coefficients are presently loaded from a documented CSV contract;
genome-coordinate remapping, batch preprocessing, containers, and external-command
execution are deliberate future extensions, not hidden fallback behavior.
