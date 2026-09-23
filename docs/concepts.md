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
