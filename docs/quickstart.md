# Quick start

Python 3.11 or later is required. Clone the repository and enter its root. For the
reproducible development environment used in CI:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements/dev.lock
python -m pip install --no-deps --no-build-isolation -e .
aging-clock version
aging-clock registry validate
```

For a normal core install, `python -m pip install .` is sufficient; `'.[mcp]'` adds
the optional MCP SDK. The locked development install additionally includes tests,
linters and build tools. No biological files are downloaded by these commands.

## Establish reference behavior first

```sh
aging-clock conformance list
aging-clock conformance run horvath-2013
aging-clock conformance run horvath-2013 --implementation python-decimal
aging-clock compare --clock horvath-2013
```

Each implementation must report 16 passed and zero failed. This is normalized
scoring only. The recorded R reference is evidence, not a live R runtime dependency.

## Inspect a public sample

```sh
python examples/export_public_fixture.py --output /tmp/acc-public-example
aging-clock validate /tmp/acc-public-example/sample.csv --clock horvath-2013 \
  --manifest /tmp/acc-public-example/sample.json
aging-clock score /tmp/acc-public-example/sample.csv --clock horvath-2013 \
  --manifest /tmp/acc-public-example/sample.json --json > /tmp/acc-public-report.json
```

The exporter requires a new directory. The public sample is conditionally applicable
under its declared normalization metadata; the default scorer also freshly passes
its reference suite. The selected reference age is approximately 60.2774909978736.
Inspect `input_validation`, `conformance`, `result`, and `provenance` separately.

## Exercise abstention

```sh
aging-clock coverage examples/incomplete.csv --clock horvath-2013
aging-clock score examples/incomplete.csv --clock horvath-2013 --json
```

Coverage succeeds as a diagnostic. Scoring exits 1 and returns null. The input has
one public reference measurement, lacks the rest of the model and supplies no
scientific manifest. No approximate result is produced.

For your own files, follow [input format](input-format.md). A complete input without
normalization evidence remains blocked. Use `--sample` for an explicit selection;
never assume the first row or column will be selected for you.

## Output and exit codes

`--json` is machine-readable and contains full lists. `--markdown` produces a concise
report. They are mutually exclusive. Use shell redirection to choose an output file.
Global `--quiet` suppresses human summaries, preserving JSON and exit codes; global
`--verbose` includes all findings. Put global flags before the command.

- **0**: successful command or diagnostic coverage report.
- **1**: scientific abstention, numerical conformance failure, or comparison failure.
- **2**: input/configuration/schema/integrity error or CLI usage error.

Application errors under `--json` use `error.code` and `error.message`. Argument
syntax errors detected by Typer before execution use its normal usage output.
