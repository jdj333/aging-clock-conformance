# Provenance and reproducibility

Scientific evidence is identified independently from runtime output. The chain is:

1. Publisher article/correction and specific supplementary files, with author,
   DOI/URL, license and source checksum.
2. Pinned upstream R run, its complete input manifest, runner checksum, package
   versions, container digest and session record.
3. Unchanged normalized fixture and independently generated expected output CSV.
4. Project-authored versioned clock and fixture definitions, with source references.
5. The execution report: implementation/version/source digest, input and manifest
   digests, fixture version, reference checksums, timestamp and runtime environment.

The explicit import allowlist is `scripts/reference-imports.json`; its identical
packaged copy is `data/public-artifacts.json`. Files include retrieval dates,
licenses, original URLs, pinned upstream revision, role, transformations and derived
relationships. `sources/upstream-suite.json` retains the hashes of full upstream
pipeline resources that are deliberately not duplicated here.

## Import without copying private upstream data

After obtaining the related repository at the documented revision:

```sh
python scripts/import_horvath.py /path/to/horvath_methylation_age --check
# To populate absent allowlisted artifacts, omit --check.
```

The importer checks upstream HEAD and every selected file's fixed hash before writing
anything. It refuses to overwrite a different existing artifact. It does not traverse
`samples/` or copy an upstream database. No personal sample is required for any test.
Fetching source data is an explicit preparatory action, never an automatic scoring
side effect. The default package already contains everything needed for `score-v1`.

## Report identity

`RunReport.run_id` is SHA-256 of canonical JSON for the complete report except the
run ID itself and `provenance.execution_timestamp`. Keys are sorted, numbers remain
unrounded, NaN/infinity are forbidden, encoding is UTF-8, indentation is two spaces,
and a final newline is present. Repeated runs with identical inputs, source versions
and runtime state have identical IDs; timestamps naturally differ.

Input checksums cover actual bytes read, not a later reread of a changing path.
CSV row ordering or line-ending changes may change an input digest and run ID while
the numerical result stays unchanged. In-memory input has a separately documented
canonical encoding; see [input format](input-format.md).

Git state is taken from this package's checkout, never from the caller's arbitrary
working directory. A source checkout records its current HEAD and dirty state.
An installed wheel without Git metadata records null rather than inventing a commit;
the package version, clock/artifact hashes and implementation source digest remain
available. Preserve the wheel hash or installation revision with published analyses.

## Trust and limits

Checksums detect divergence from a reviewed manifest. They do not authenticate the
publisher, establish processing quality, or prove that submitted metadata is true.
The manifest itself is trusted through the versioned source/distribution you install.
No clinical or population validity is inferred from computational agreement.

Two builds use the same fixed `SOURCE_DATE_EPOCH`, verify wheel and source-archive
bytes, and execute the installed wheel outside the checkout. This establishes a
repeatable build within the tested toolchain; it does not promise byte-identical
archives across every future build-backend release.
