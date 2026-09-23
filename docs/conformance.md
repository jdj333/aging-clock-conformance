# Reference conformance and implementation comparison

## The initial claim

`score-v1` tests **already normalized beta values → linear score → DNAm age** for
the complete 353-CpG Horvath predictor. It does not run BMIQ, raw IDAT processing,
coordinate mapping, assay harmonization, or missing-value imputation.

The public fixture is `horvath-2013-publisher-normalized-v1`, version `1.0.0`.
Its 16 samples are the publisher tutorial's GSE38608 occipital-cortex subset,
measured on Illumina 27K arrays. There is no personal sample in the bundle.
The normalized matrix and expected CSV are unchanged imports from the independently
executed upstream R reference run. The included session record identifies R 4.5.2,
RPMM 1.25, cluster 2.1.8.1, and Linux/arm64. This package does not claim a fresh R
normalization run merely because those historical artifacts are available.

## Model and arithmetic

Publisher Additional file 23 supplies 353 identifiers and `CoefficientTraining`
weights, plus intercept `0.695507258`. Additional file 20 defines the inverse:

```text
linear_score = intercept + sum(weight_i * normalized_beta_i)
age = 21 * exp(linear_score) - 1    if linear_score < 0
age = 21 * linear_score + 20       otherwise
```

`python-fsum` uses binary64 products and `math.fsum` in publisher coefficient order.
`python-decimal` converts the same binary64 inputs and coefficients exactly to
Decimal, then uses a fresh 50-digit, round-half-even context and independently
written summation/transform code. Neither rounds stored results. Both enforce the
same input gate and compare against frozen R results. Their agreement is an
arithmetic check, not an independent validation cohort or normalization method.

## Tolerances and expectations

Absolute tolerance: **linear score `1e-12`; result `1e-10` years**. These are the
upstream reference-environment tolerances for the unchanged serialized normalized
matrix, not biological error bars. Tolerances account for serialized floating-point
values and arithmetic differences; they must not be increased to rescue a failing
implementation. The publisher's displayed ages are separately checked at two
significant digits. The tutorial DOCX and the exact expected CSV are checksummed.

Every case includes expected/observed values, score and age differences, relative
age difference (null if the expected value is zero), status and findings. Comparison
requires both absolute scores/ages to pass against the independent reference and
each pair of executed implementations to agree within the corresponding tolerance.
Two equally wrong implementations cannot pass just by agreeing with one another.

```sh
aging-clock conformance list
aging-clock conformance run horvath-2013 --implementation python-decimal --json
aging-clock compare --clock horvath-2013 \
  --implementation python-fsum --implementation python-decimal --json
```

`reference-r-recorded` identifies expected evidence, not an executable adapter ID.
Passing a suite means all 16 samples passed; a malformed or corrupt fixture is an
integrity/configuration error, not a numerical comparison failure.

## Preprocessing and conservative profile policy

The original tutorial contains imputation branches. This project does not implement
them and requires all 353 values for its score-only profile. The published method's
full preprocessing requires resources beyond those 353 probes. Supplying a complete
targeted panel therefore cannot establish compatibility. The profile accepts only
explicitly declared publisher BMIQ calibration against the exact Additional file 22
reference, a provenance record, and a matching input checksum. Declarations remain
conditional; checksums do not audit a laboratory or prove normalization occurred.

Genome build is optional because exact CpG identifiers are matched without coordinate
conversion. The accepted tissue and platform lists are conservative subsets with
publication sources. Newer arrays, unspecified tissues, alternate normalization,
and imputation remain unsupported until separately justified and tested.

## Reproducing the upstream normalization

Use the [pinned upstream runner and container instructions](https://github.com/jdj333/horvath_methylation_age/tree/c3d1cfe1beb162add6ce8c1a1c21606f89c8a64a/conformance).
The complete source hashes and pinned container digest are preserved locally in
`sources/upstream-suite.json`. The large raw matrix and normalization annotation
are intentionally not duplicated. A future live R or independent normalization
adapter must report a distinct stage and must not inherit upstream status flags.
