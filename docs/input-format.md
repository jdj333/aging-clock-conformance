# Input and manifest contract

Formats are explicit. Nothing infers tissue, species, modality, array platform,
normalization, or genome build from a filename or the presence of CpG identifiers.

## Long CSV (default)

```csv
feature_id,value
cg00075967,0.5
```

This two-column snippet is a **synthetic syntax example**, not a reference sample.
Optional columns: `sample_id`, `unit`, `source_column`, `quality_flag`. Unknown or
duplicate headers, ragged rows, malformed quoting, and non-UTF-8 bytes are rejected.
UTF-8 BOMs are accepted. Feature identifiers are case-sensitive and are not trimmed.
Numeric whitespace is accepted explicitly; numeric underscores, thousands
separators, locale decimal commas, and Unicode digits are rejected.

Rows for different `sample_id` values require `--sample ID` or a manifest naming the
selected sample. A conflicting explicit selection and manifest is an error.
A two-column file can be labeled by the manifest; otherwise it receives the visible
placeholder `unidentified-sample`. Duplicate feature rows are always preserved until
validation and never averaged or overwritten.

## Matrix CSV

```csv
feature_id,sample-a,sample-b
cg00075967,0.5,0.4
```

Use `--format matrix` or `input_format: matrix` in the manifest. The first column
must be `feature_id` or `probe_id`; the remaining headers are exact sample IDs. A
multi-sample matrix always requires explicit selection. Sample-by-feature wide
files are not supported and are never silently reduced to their first row.

## Manifest

Use JSON or safe YAML, validated against
[`sample-manifest.schema.json`](../schemas/sample-manifest.schema.json). Duplicate
keys are rejected, including nested keys. Extra fields and scalar type coercion
are disallowed. Omit unavailable scientific metadata or use explicit nulls.

```yaml
schema_version: '1.0'
sample_id: example-001
modality: dna_methylation
species: Homo sapiens
tissue: whole_blood
sample_type: DNA
assay:
  method: bisulfite_array
  platform: illumina_450k
unit: beta_fraction
genome_build: null
preprocessing:
  stage: normalized_beta
  normalization: horvath-2013-bmiq
  reference_sha256: e4ea35396c429df1ea3ee64a3c0a012be16eba365ca5b8ae17328bbee13d2dd5
  evidence: null
measurements: sample.csv
measurements_sha256: null
input_format: long
```

This deliberately incomplete manifest **blocks** until a real preprocessing
provenance record and correct input checksum are supplied. Never fill these fields
merely to satisfy a validator. `measurements` is relative to the manifest directory
and must identify the explicitly supplied input file. `measurements_sha256` hashes
the entire original CSV bytes, including headers, line endings, and every sample
column. Selection is recorded separately; the original matrix is not rewritten.

Get a file digest without uploading it:

```sh
python -c 'import hashlib,pathlib; print(hashlib.sha256(pathlib.Path("sample.csv").read_bytes()).hexdigest())'
```

## Values and units

For the Horvath score profile, all 353 required beta fractions must be in `[0, 1]`.
Empty strings, `NA`, `N/A`, `null`, and `None` (case-insensitive) are explicit missing
values. NaN, infinity, numeric overflow, and nonzero values that underflow binary64
are rejected. No value is clamped, imputed, transformed from a percentage, or
silently converted from an M-value.

A unit must be declared in the manifest or in every row. Row units must agree with
the manifest if both are supplied. `quality_flag` may be absent or `PASS`; other
values block this initial profile. It is a supplied assertion, not an independent
quality-control procedure.

## Inline Python/MCP data

`inline_sample(tuple[Measurement, ...], metadata)` never opens paths or URLs. It
rejects a non-null `measurements` path. The inline checksum is SHA-256 of UTF-8
canonical JSON for the ordered list of `Measurement.model_dump()` records, with
all optional fields present, sorted keys, two-space indentation, and a final newline.
Use `inline_sample(...).input_sha256` to inspect the checksum; then bind a genuine
preprocessing record to that input. Do not copy a CSV file digest onto differently
serialized inline data. Validation reports expose the digest they actually checked.
