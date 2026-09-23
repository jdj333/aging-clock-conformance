"""Validate every row before constructing any feature-to-value mapping."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from ..models import FeatureContract, Finding, Measurement, Severity

NUMERIC = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")
NULL_TOKENS = frozenset({"", "na", "n/a", "null", "none"})


def parse_value(value: str | float | int | None) -> tuple[float | None, str | None]:
    if value is None or (isinstance(value, str) and value.strip().lower() in NULL_TOKENS):
        return None, "ACC_NULL_VALUE"
    if isinstance(value, bool):
        return None, "ACC_NONNUMERIC_VALUE"
    if isinstance(value, str):
        token = value.strip()
        if token.lower().lstrip("+-") in {"nan", "inf", "infinity"}:
            return None, "ACC_NONFINITE_VALUE"
        if not NUMERIC.fullmatch(token):
            return None, "ACC_NONNUMERIC_VALUE"
    try:
        numeric = float(value)
    except (ValueError, OverflowError):
        return None, "ACC_NONFINITE_VALUE"
    if not math.isfinite(numeric):
        return None, "ACC_NONFINITE_VALUE"
    if numeric == 0.0 and isinstance(value, str) and Decimal(value.strip()) != 0:
        return None, "ACC_NUMERIC_UNDERFLOW"
    return numeric, None


@dataclass(frozen=True)
class CheckedValues:
    present: frozenset[str]
    usable: tuple[tuple[str, float], ...]
    findings: tuple[Finding, ...]


def check_values(
    rows: tuple[Measurement, ...], contract: FeatureContract, declared_unit: str | None
) -> CheckedValues:
    groups: dict[str, list[tuple[Measurement, float | None, bool]]] = defaultdict(list)
    findings: list[Finding] = []
    messages = {
        "ACC_NULL_VALUE": "Measurement is explicitly missing; no imputation is performed.",
        "ACC_NONNUMERIC_VALUE": "Measurement is not a supported numeric value.",
        "ACC_NONFINITE_VALUE": "Measurement is NaN, infinite, or overflows binary64.",
        "ACC_NUMERIC_UNDERFLOW": "Nonzero measurement underflows binary64; "
        "it is not replaced by zero.",
    }
    for index, row in enumerate(rows, start=1):
        feature = row.feature_id
        valid = True
        if not feature:
            findings.append(
                Finding(
                    code="ACC_FEATURE_ID_MISSING",
                    severity=Severity.BLOCKING,
                    category="data_quality",
                    message="Measurement has no feature identifier.",
                    row=index,
                )
            )
            continue
        if not re.fullmatch(contract.identifier_pattern, feature):
            findings.append(
                Finding(
                    code="ACC_MALFORMED_IDENTIFIER",
                    severity=Severity.BLOCKING,
                    category="data_quality",
                    message="Feature identifier violates the clock contract.",
                    feature_id=feature,
                    row=index,
                )
            )
            valid = False
        numeric, error = parse_value(row.value)
        if error:
            findings.append(
                Finding(
                    code=error,
                    severity=Severity.BLOCKING,
                    category="data_quality",
                    message=messages[error],
                    feature_id=feature,
                    row=index,
                )
            )
            valid = False
        if numeric is not None and (
            (contract.minimum is not None and numeric < contract.minimum)
            or (contract.maximum is not None and numeric > contract.maximum)
        ):
            findings.append(
                Finding(
                    code="ACC_VALUE_OUT_OF_RANGE",
                    severity=Severity.BLOCKING,
                    category="data_quality",
                    message="Measurement is outside the clock's declared range.",
                    feature_id=feature,
                    row=index,
                )
            )
            valid = False
        unit = row.unit or declared_unit
        if unit and unit != contract.unit:
            findings.append(
                Finding(
                    code="ACC_UNEXPECTED_UNIT",
                    severity=Severity.BLOCKING,
                    category="data_quality",
                    message="Measurement unit differs from the clock contract.",
                    feature_id=feature,
                    row=index,
                )
            )
            valid = False
        if row.unit and declared_unit and row.unit != declared_unit:
            findings.append(
                Finding(
                    code="ACC_UNIT_CONFLICT",
                    severity=Severity.BLOCKING,
                    category="data_quality",
                    message="Row and manifest units conflict.",
                    feature_id=feature,
                    row=index,
                )
            )
            valid = False
        if row.quality_flag and row.quality_flag != "PASS":
            findings.append(
                Finding(
                    code="ACC_QUALITY_FLAG",
                    severity=Severity.BLOCKING,
                    category="data_quality",
                    message="Only an absent or PASS quality flag is supported.",
                    feature_id=feature,
                    row=index,
                )
            )
            valid = False
        groups[feature].append((row, numeric, valid))
    usable = []
    for feature in sorted(groups):
        group = groups[feature]
        if len(group) > 1:
            # None, invalid tokens, and finite values stay distinguishable for conflict reporting.
            signatures = {
                (
                    number if number is not None else (type(row.value).__name__, repr(row.value)),
                    row.unit,
                )
                for row, number, _ in group
            }
            conflicting = len(signatures) > 1
            findings.append(
                Finding(
                    code="ACC_CONFLICTING_DUPLICATE" if conflicting else "ACC_DUPLICATE_FEATURE",
                    severity=Severity.BLOCKING,
                    category="data_quality",
                    feature_id=feature,
                    message="Feature has conflicting duplicate measurements."
                    if conflicting
                    else "Feature occurs more than once; duplicates are never collapsed.",
                )
            )
        elif group[0][2] and group[0][1] is not None:
            usable.append((feature, group[0][1]))
    if not rows:
        findings.append(
            Finding(
                code="ACC_EMPTY_INPUT",
                severity=Severity.BLOCKING,
                category="data_quality",
                message="Sample has no measurements.",
            )
        )
    return CheckedValues(frozenset(groups), tuple(usable), tuple(findings))
