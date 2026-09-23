# Separate scientific claims

Reports expose ten independent dimensions. No dimension promotes another one merely
because it passed.

| Dimension | Meaning in this release |
| --- | --- |
| Schema validity | Input structure and checksum binding; parser errors use a structured error envelope |
| Input-data quality | Identifier, uniqueness, value, unit, range, and quality-flag checks |
| Feature coverage | Complete only if every required feature has one usable value |
| Preprocessing compatibility | Unknown, incompatible, or compatible **as declared** |
| Assay/platform compatibility | Whether declarations match this profile's accepted vocabulary |
| Tissue compatibility | Whether the declared tissue is in the explicit supported subset |
| Computational applicability | Deterministic permission/abstention decision under the profile |
| Reference conformance | `NOT_RUN`, `REFERENCE_CONFORMANT`, or `NONCONFORMANT` for an actual run |
| External validation | `NOT_ASSESSED` for the submitted population by this toolkit |
| Clinical validity | `NOT_ESTABLISHED` by this toolkit |

## Applicability states

| Status | `can_compute` | Meaning |
| --- | --- | --- |
| `CONDITIONALLY_APPLICABLE` | true | All implemented checks pass, conditional on supplied scientific metadata/provenance |
| `INSUFFICIENT_METADATA` | false | Required metadata or preprocessing evidence is missing/unknown |
| `NOT_APPLICABLE` | false | Invalid data, missing features, incompatible declarations, or failed reference conformance |
| `UNSUPPORTED` | false | Requirement policy or execution implementation is unavailable |
| `APPLICABLE` | reserved | Not emitted by this release; reserved for a future independently verified preprocessing provenance contract |

Unsupported policy takes precedence, then observed incompatibility/data errors,
then metadata gaps. All blockers remain in `reasons`, regardless of the summary
state. Thus an incomplete sample with missing normalization reports both problems,
even though its overall status is `NOT_APPLICABLE`.

A checksum proves which bytes were examined. It cannot prove what happened in a
laboratory. An evidence URL is recorded without being fetched, evaluated, or treated
as independently verified. Tokens such as `unknown`, `unresolved`, and
`not_documented` cannot satisfy required provenance.

## Findings and stable codes

Findings have a stable `code`, `severity`, `category`, human message, and optional
feature ID and row number. Messages may improve between releases; integrations
should branch on codes and structured states rather than matching message text.
Categories are `schema`, `data_quality`, `coverage`, `metadata`, and `implementation`.

| Severity | Effect |
| --- | --- |
| `INFO` | Observation; does not independently block computation |
| `WARNING` | Explicit assumption or limitation; may accompany conditional applicability |
| `ERROR` | Failed validation/conformance check; prevents a passing computation decision |
| `BLOCKING` | An unmet prerequisite that prevents computation |

Representative codes (the actual report retains every observed reason):

| Code or family | Meaning |
| --- | --- |
| `ACC_DUPLICATE_FEATURE`, `ACC_CONFLICTING_DUPLICATE` | Repeated feature measurements; never collapsed |
| `ACC_FEATURE_ID_MISSING`, `ACC_MALFORMED_IDENTIFIER` | Absent or invalid identifier |
| `ACC_NULL_VALUE`, `ACC_NONNUMERIC_VALUE` | Explicit missing value or unsupported numeric text |
| `ACC_NONFINITE_VALUE`, `ACC_NUMERIC_UNDERFLOW` | NaN/infinity/overflow or nonzero-to-zero underflow |
| `ACC_VALUE_OUT_OF_RANGE`, `ACC_UNEXPECTED_UNIT`, `ACC_UNIT_CONFLICT` | Range or unit violation |
| `ACC_MISSING_FEATURES`, `ACC_EXTRA_FEATURES` | Required features absent; extra features observed |
| `ACC_<FIELD>_UNKNOWN`, `ACC_<FIELD>_MISMATCH` | Missing/unknown or incompatible modality, species, tissue, assay, platform, units, or preprocessing |
| `ACC_PREPROCESSING_UNVERIFIED`, `ACC_PREPROCESSING_UNBOUND` | Missing normalization record or input checksum binding |
| `ACC_PREPROCESSING_DECLARED` | Processing history remains a caller declaration |
| `ACC_SAMPLE_SELECTION_REQUIRED`, `ACC_UNKNOWN_SAMPLE` | Ambiguous or absent sample selection |
| `ACC_INPUT_CHECKSUM_MISMATCH`, `ACC_CHECKSUM_MISMATCH` | Submitted input or reference artifact integrity failure |
| `ACC_IMPLEMENTATION_UNAVAILABLE`, `ACC_REQUIREMENT_UNRESOLVED` | Execution or scientific contract is unsupported |
| `ACC_REFERENCE_MISMATCH`, `ACC_REFERENCE_NONCONFORMANT` | Numerical mismatch or public scoring blocked by a failed reference suite |

File/parser/configuration errors that prevent creation of a Sample use the
application error envelope (`error.code`, `error.message`) instead of pretending a
partial scientific report passed. CLI exit semantics are in [quick start](quickstart.md).

## Coverage arithmetic

Counts refer to unique identifiers. `present_count` includes required identifiers
with null or invalid values. `valid_numeric_count` includes only uniquely observed,
finite, in-range, correctly annotated required measurements. Duplicates are unusable,
even if their values agree. `invalid_count = present_count - valid_numeric_count`;
`missing_count = required_count - present_count`. Extra features are separate.

Invalid extra rows still fail input-data quality; valid extras do not change the
score. This conservative sample contract avoids silently discarding malformed input.
Unknown units do not change numerical coverage, but they block applicability.

## Conformance terminology

`UNVERIFIED` means no relevant reference evidence has been executed. A claim limited
to one stage can be described as partially verified for a larger pipeline, but the
actual report names the precise passing profile. `REFERENCE_CONFORMANT` always means
all cases in the specified fixture/version passed at the declared tolerance. It
does not mean all conceivable inputs, populations, or preprocessing pipelines pass.
