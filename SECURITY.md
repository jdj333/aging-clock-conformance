# Security policy

The current `0.1.x` development line receives fixes; there is no hosted production
service or authenticated HTTP API in this repository. The MCP server is local stdio
and its tools accept inline data only.

Report security defects privately through the repository's
[GitHub security advisory form](https://github.com/jdj333/aging-clock-conformance/security/advisories/new)
when available. If private reporting is unavailable, open a minimal issue requesting
a private contact channel, without exploit details, secrets, biological data, or
identifying reports. Do not claim an issue was privately disclosed merely because
a public issue exists.

Useful reports include the package/revision, affected entry point, a minimal
synthetic reproducer, expected behavior and impact. In particular, report ways to
bypass computation gates, silently overwrite features, accept non-finite numbers,
read arbitrary local files through MCP, or escape registry artifact paths.

Scientific discrepancies may also be correctness issues: preserve the reference
artifact and supply a public source citation. Do not change coefficients or expected
values as a security workaround. See [privacy guidance](docs/privacy.md) before
sharing any diagnostic output.
