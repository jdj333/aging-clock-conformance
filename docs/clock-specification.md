# Clock specification v1

The executable contract is `ClockDefinition` in `models.py`, exported deterministically
as [`schemas/clock.schema.json`](../schemas/clock.schema.json). Registry files are
JSON; sample manifests can also be YAML. Schema version and scientific clock
definition version are separate fields.

The default clock lives under
`src/aging_clock_conformance/data/clocks/horvath-2013/clock.json`. It contains:

- Stable identity, aliases, definition version, publication year/source, target and units.
- Explicit requirements for modality, species, tissue, sample type, assay and platform.
  Each requirement has a `status`, finite `accepted` vocabulary, `source_ids`, and scope note.
- A feature contract with identifier pattern, expected count, units and optional bounds.
- Checksummed coefficient artifact, exact identifier/coefficient columns, intercept label/value.
- Adapter transformation identifier, parameter and formula description with sources.
- Explicit input stage, normalization/reference hash, evidence requirement and missing-data policy.
- Implementation IDs, checksummed fixture manifest, external/clinical validation status and notes.
- Source records with authors, URLs/DOIs, licenses, retrieval dates, locators and revisions.

`UNKNOWN` and `UNSUPPORTED` requirements are schema-valid but do not permit execution.
All scientific source references must resolve to declared source records. The field
`scientific_source_ids` also attributes the identity/output/profile-policy facts.
The current `complete_required` policy is implemented; other policies must be
represented as unsupported until their algorithm and conformance evidence exist.

## Integrity constraints beyond JSON Schema

The loader verifies every byte digest and disallows escaping paths. It checks exactly
one intercept, consistency with the declared value, unique feature IDs, finite
coefficients, exact count, identifier syntax, unique clock IDs/aliases and source IDs.
Fixture loading checks stage/clock agreement, unique samples, feature order, expected
output column mappings, published display consistency and supporting artifact hashes.

`integrity.json` inventories the packaged registry, including manifests. It is an
integrity check, not a digital signature. Its trust anchor is the reviewed repository
revision or distribution you installed; a party able to replace both data and all
hashes can create a different registry. Published provenance must identify that
revision and the observed definition digest.

## Updating a definition

Edit a definition only for an explicitly justified scientific or contract change.
Existing released fixtures remain immutable. Introduce a new version for changed
inputs, outputs, tolerances, or metadata assertions that alter applicability.
Update the fixture-manifest digest when appropriate, regenerate schemas only for
type changes, then rebuild the package inventory and inspect all diffs. Never
replace the canonical coefficient table merely to accommodate a new platform.
