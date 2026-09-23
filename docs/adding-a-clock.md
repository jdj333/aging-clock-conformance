# Adding a clock

A clock is supported only when its specification, provenance, executable adapter,
and independent fixture all exist. Adding a name or coefficient list is not enough.

1. **Research the method.** Locate the primary publication, corrections, original
   coefficients/transforms, preprocessing resources, missing-data behavior, assay
   and tissue scope. Separate published facts from your conservative implementation
   profile. Record unresolved details; block execution if they can change a result.
2. **Establish rights.** Review redistribution licenses before importing anything.
   Use a small explicit artifact allowlist, exact hashes and source URLs. Exclude
   personal data and preserve third-party notices.
3. **Define the contract.** Add `data/clocks/<clock-id>/clock.json` and versioned
   artifacts. Every scientific requirement needs a source record and locator.
   Do not infer support for newer assays or inherit a global coverage threshold.
4. **Implement the adapter.** Implement `ClockAdapter` in `adapters/`, enforce the
   shared input gate, verify model integrity, and identify version, source digest,
   deterministic arithmetic and supported stage. Register only the intended IDs.
   Do not put formulas or permissive fallbacks in CLI/MCP code.
5. **Obtain independent expectations.** Use publisher outputs or an audited,
   independently executed reference method. Specify immutable fixture ID/version,
   input-stage description, metadata, expected applicability, expected outputs,
   checksums and scientifically justified absolute tolerances. Never call the new
   adapter to create its own golden results.
6. **Test failure as well as success.** Cover duplicates, missing values, NaN/inf,
   bounds and units, metadata gaps, incompatible preprocessing/platforms/tissues,
   corrupted coefficients/fixtures, wrong transforms, ordering, extra features,
   CLI exit codes and MCP/API consistency.
7. **Verify and document.** Run the complete commands in [development](development.md),
   update supported-clock tables only after evidence passes, and record limitations.

## Fixture mapping

`FixtureSuite` maps column names in a frozen expected CSV to sample ID, linear
score, and scalar result. An optional published rounded-output column must specify
its significant digits. Samples are unique, metadata IDs must agree, input feature
order must match the coefficient source, and expected statuses must be tested.
All referenced files remain below the registry root and have exact SHA-256 values.

The current shared representation supports numeric weighted score profiles and
complete required features. Introduce a versioned contract for multi-output clocks,
documented missing-data preprocessing, or a materially different fixture shape;
do not hide those differences under the Horvath adapter.

## Next candidate

**Hannum's blood methylation clock** is a useful next engineering target: it shares
the methylation modality while testing a distinct, blood-focused contract. This is
a prioritization recommendation, not a support claim. Begin with the
[primary publication](https://doi.org/10.1016/j.molcel.2012.10.016) and verify source
rights, exact coefficients, preprocessing, and independent expected outputs before
implementation. No Hannum definition or calculation is shipped in this release.
