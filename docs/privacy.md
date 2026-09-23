# Privacy

The default execution path is local. The package has no telemetry, biological-data
uploads, network API calls, or cloud database. The MCP server runs over local stdio
and accepts inline measurements; none of its tools takes arbitrary local paths,
executes supplied commands, or fetches evidence URLs. The deterministic core does
not import or depend on an LLM SDK.

## Samples versus fixtures

Only public publisher-derived conformance samples are packaged. Private user data
belongs outside the repository, for example in the ignored `private/` directory.
Do not attach personal biological files or reports to issues, pull requests, or CI
artifacts. A report contains the supplied sample identifier, findings, feature IDs
where relevant, checksums, and potentially a calculated age. Those can still be
sensitive even though full input measurements are omitted.

Use pseudonymous sample IDs when possible. No username, hostname, patient identity,
or absolute input path is collected in a report. Runtime platform and package
versions are recorded to support reproducibility. The core does not create temporary
copies of private sample data. Public example export writes only to an explicit new
directory and refuses overwrites.

## Client boundary

Local MCP processing does not determine an AI client's privacy policy. A hosted
agent can see the inline data that its user asks it to submit and the tool results
it receives. Choose data and client settings accordingly. This repository does not
configure clients, upload biological files, expose an HTTP service, or enable a
remote server on behalf of the user.

Parser/type errors avoid echoing full file contents. Expected validation findings
carry stable codes and locations rather than raw measurement values. Exported JSON
and Markdown are user-controlled files; protect and delete them under the same
policy as their inputs.
