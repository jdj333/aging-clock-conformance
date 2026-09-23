# Contributing

Start with [AGENTS.md](AGENTS.md), the scientific invariants, and
[development](docs/development.md). Focus changes on reproducibility, explicit
requirements, and safe abstention. A useful pull request explains the concrete
behavior changed, its source evidence, and checks that demonstrate it.

For a new clock, follow [adding a clock](docs/adding-a-clock.md). For reference
changes, preserve released fixtures, introduce a new version and explain why the
scientific contract changed. Never generate expected reference results using the
same implementation being tested, replace missing features to make a test pass,
or widen tolerances without a documented numerical justification.

Keep scientific state in source-backed registry records and adapters; CLI and MCP
must reuse core functions. Keep generated schemas synchronized with typed models.
Do not hand-edit imported scientific artifacts. Include license provenance for new
data and preserve attribution. No private biological files, credentials, or raw
personal-data reports belong in a pull request.

Run all commands in [development](docs/development.md), including the installed-wheel
check. Tests should expose scientific failure modes, not merely assert implementation
details. Report which runtime(s) were actually tested and any unverified scope.

This project accepts improvements to documentation and source auditability as first-
class contributions. Avoid advertising planned clocks, pipelines or validation
populations as existing support.
