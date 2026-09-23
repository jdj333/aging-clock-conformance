# Source research and initial design decisions

Reviewed 2026-09-20 before implementation.

## Horvath reference repository

Inspected [jdj333/horvath_methylation_age at
c3d1cfe1beb162add6ce8c1a1c21606f89c8a64a](https://github.com/jdj333/horvath_methylation_age/tree/c3d1cfe1beb162add6ce8c1a1c21606f89c8a64a):
the normative score specification, publisher source catalog, conformance manifest,
R runner and session information, expected CSVs, Python checker, schemas, and MCP
architecture. The local checkout matched the public main revision at review time.

The useful reusable boundary is **normalized 353-probe beta values → linear score
→ inverse age transformation**. Its 16 public tutorial samples have exact outputs
from R 4.5.2 / RPMM 1.25 / cluster 2.1.8.1 and independently published rounded ages.
The general framework will recompute the score profile itself; it must not inherit
upstream's `pipeline-v1: passing` flag as evidence for its own normalization code.
No normalization implementation is included in the initial execution path.

Read the publisher [2013 article and supplements](https://doi.org/10.1186/gb-2013-14-10-r115)
and [2015 correction](https://doi.org/10.1186/s13059-015-0649-6).
The supported coefficient column is `CoefficientTraining`, not the shrunken model.
The intercept and inverse transform are taken from the predictor and tutorial.
The publisher's tutorial has missing-value branches; the initial complete-input
score profile deliberately does not implement those upstream pipeline branches.
This restriction is a framework profile decision, not a claim that the publication
universally forbids imputation. The normalization annotation has 21,368 rows whereas
the article mentions 21,369: preserve the artifact and document the discrepancy.

## Redistribution and data minimization

The publisher rights notice grants CC BY 2.0. The upstream NOTICE applies this to
the supplementary material and identifies its newly written software as MIT.
Retain both attributions. Import only the unchanged coefficient table and the
small, public normalized fixture, expected values, R session record, tutorial,
source scoring script, and reference runner needed to audit the score profile.
Track original source URLs, SHA-256, upstream revision, and transformations.
Keep full raw matrices and normalization resources upstream; allow explicit
checksum-verified reimport from an existing checkout. Do not copy its personal
sample, derived private datasets, database, or unlicensed educational code.

## LongevityClaw integration boundary

Inspected [Insilico-org/longeclaw at
dd6861cb280d5ffba0c81766a405a702d0b3acef](https://github.com/Insilico-org/longeclaw/tree/dd6861cb280d5ffba0c81766a405a702d0b3acef),
including `predict.py`, `tools.py`, `agent.py`, and package configuration.
Its agent calls domain tools over a clock database, then interprets results.
At this revision, the prediction path selects clocks using feature coverage,
can select a first sample row, and constructs a dictionary from measurement pairs.
These observations identify useful integration points: validate before selection
and scoring, preserve duplicate rows, require explicit sample selection, and return
structured abstention reasons to the calling agent. No LongevityClaw code or data
is imported, and no compatibility with its entire clock database is claimed.

## Schema and execution design

Use immutable typed models, JSON Schema 2020-12, a packaged JSON registry, explicit
long/matrix CSV contracts, and small pure validation functions. Every scientific
requirement names its source records. Represent unknowns and unsupported scopes
directly. Manifest normalization declarations can establish conditional computational
applicability, never independent verification of how a private sample was processed.
Use Python binary64 summation and a separate Decimal arithmetic path; compare both
with the independently produced, frozen R outputs. Separate historical R evidence
from computations executed during the current run. MCP is optional, local stdio,
accepts inline measurements, and calls the same application API as the CLI.
