# Development and verification

Use Python 3.11+. The committed `requirements/dev.lock` pins the full development
and optional MCP environment with distribution hashes, including build tools.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements/dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m pip check
```

Core runtime requirements are deliberately small: Pydantic, Typer/Rich and PyYAML.
No pandas, NumPy, database, R runtime, or LLM is needed. MCP is an optional extra.
The package declares a tested Typer minor range because recent Typer releases
changed their Click integration; CLI code does not depend on a separate Click context.

## Required checks

```sh
ruff check .
ruff format --check .
mypy src
pytest --cov=aging_clock_conformance --cov-report=term-missing
python scripts/generate_schemas.py --check
python scripts/check_artifacts.py
aging-clock registry validate
aging-clock conformance run horvath-2013
aging-clock conformance run horvath-2013 --implementation python-decimal
aging-clock compare --clock horvath-2013
python scripts/check_build.py
```

The test suite covers schema/contracts, values and metadata, negative inputs,
scientific invariants, independent reference outputs, tampered models/fixtures,
CLI exit/JSON behavior, report/provenance serialization, and MCP protocol equivalence.
Row-order and valid-extra-feature invariants are tested over deterministic
permutations. Numerical golden expectations are imported, never produced by the
Python implementation under test. Coverage helps identify unexamined paths; it is
not a scientific validity metric or a goal of reaching a decorative percentage.

`check_build.py` performs two fixed-epoch builds, compares wheel and sdist bytes,
then installs and exercises the wheel outside the checkout. CI runs on Python
3.11–3.14 with no secrets and uploads only public fixture reports. Actions are pinned
to reviewed commit IDs. Source code checks and downloaded dependency installation
are separate from offline scientific execution.

## Generated files and dependency updates

```sh
python scripts/generate_schemas.py
python scripts/update_integrity.py
pip-compile --extra dev --extra mcp --generate-hashes --allow-unsafe \
  --no-emit-index-url --no-emit-trusted-host \
  --output-file requirements/dev.lock pyproject.toml
```

Regenerate schemas only after model changes. Rebuild integrity metadata only after
reviewing intended source/spec changes; this does not authorize changing fixed
source digests or released expected values. Dependency resolution needs network
access; review lock changes and rerun the entire Python matrix. Dependabot opens
dependency/action proposals, but scientific artifacts never auto-update.

## Review before release

Inspect source provenance and licensing, scientific assumptions, every route to
scoring, missing-data handling, dictionary construction, float edge cases, unknown
metadata, source integrity, CLI/docs consistency, and private-data exclusions.
Run README commands and the installed-wheel check. Distinguish local success,
committed/pushed state, and the actual hosted workflow result in release notes.
