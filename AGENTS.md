# Aging Clock Conformance: instructions for contributors and agents

Build local, deterministic research infrastructure that validates inputs and tests
implementations against independently obtained references. Feature coverage,
applicability, computational conformance, population validation, and clinical
validity are separate claims. Preserve that separation in code, tests, and prose.

## Scientific invariants

- Never invent coefficients, identifiers, transforms, normalization, expected
  results, tissue/platform support, missing-data policies, or validation claims.
- Source precedence: publisher corrections and method artifacts; publisher
  tutorial; pinned, independently reproduced reference run; other implementations.
  Resolve discrepancies explicitly; a convenient implementation is not authority.
- Unknown metadata stays unknown. No inferred modality, tissue, platform, genome
  build, or normalization. Caller declarations are not independently verified facts.
- Never impute or discard required features to obtain a score. There is no global
  coverage threshold. The initial score profile requires every model feature.
- Preserve measurement rows until duplicates have been checked. Never use a
  dictionary conversion that silently overwrites duplicate input identifiers.
- Reject nonnumeric, non-finite, invalid-range, and conflicting duplicate values.
- All public scoring routes, including adapters, must enforce the same validation
  and applicability gate. UI and MCP modules must contain no scientific formulas.
- Name the tested pipeline stage. Normalized-beta scoring does not establish raw
  IDAT processing or normalization conformance. A recorded R result is not a live run.
- Conformance does not establish clinical utility or population-specific validity.

## Adding clocks and changing references

Follow `docs/adding-a-clock.md`. A supported clock needs a validated specification,
field-level source references, licensed artifacts, immutable versioned fixtures,
independent expected results, tolerances, an adapter, and negative tests. Unsupported
clocks must not appear in the supported list. Never generate a golden expectation
with the implementation under test. Reference changes require a new fixture/spec
version and a documented scientific reason; never relax tolerances to hide failure.

## Files and privacy

Packaged scientific assets under `src/aging_clock_conformance/data/` are the single
source of truth. The importer accepts an explicit public-file allowlist from a
pinned upstream revision and verifies every digest. Never recursively copy upstream
repositories: they may contain personal data. Schemas and integrity metadata are
generated deterministically; use their scripts and inspect the resulting diff.
No telemetry, uploads, private samples, full-sample logging, secrets, or arbitrary
local-file access through MCP. Do not relicense third-party data as MIT. Read
`NOTICE.md` and `docs/licensing.md` before importing an artifact.

## Verification

Use a local virtual environment and `requirements/dev.lock`. Run:

```sh
ruff check .
ruff format --check .
mypy src
pytest
python scripts/generate_schemas.py --check
python scripts/check_artifacts.py
aging-clock registry validate
aging-clock conformance run horvath-2013
aging-clock compare --clock horvath-2013
python scripts/check_build.py
```

Tests must enforce scientific invariants and fail for corrupted coefficients,
fixtures, metadata gaps, invalid values, and altered implementations. Verify wheel
installation outside the checkout. State what was tested locally versus in hosted
CI; never claim a remote workflow ran without evidence.
