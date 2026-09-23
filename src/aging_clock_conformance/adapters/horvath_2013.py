"""Horvath score-v1, derived from publisher Supplement 20 and CoefficientTraining.

This module does not normalize, impute, or estimate from incomplete measurements.
The Decimal path intentionally implements its own arithmetic and inverse transform.
Both are compared with independently generated R outputs, not with each other's
newly generated expectations.
"""

from __future__ import annotations

import math
import platform
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path

from ..errors import ACCError
from ..models import ImplementationMetadata, Sample, ScoreResult
from ..registry import Clock
from ..serialization import sha256_file
from .base import validated_values

ADULT_AGE = 20.0  # Publisher Supplement 20, anti.trafo adult.age=20.


def inverse_age(linear_score: float, adult_age: float = ADULT_AGE) -> float:
    if not math.isfinite(linear_score) or adult_age != ADULT_AGE:
        raise ACCError(
            "ACC_TRANSFORM_INPUT",
            "Horvath score-v1 requires a finite score and the published adult age.",
        )
    return (
        (adult_age + 1) * math.exp(linear_score) - 1
        if linear_score < 0
        else (adult_age + 1) * linear_score + adult_age
    )


def _check_profile(clock: Clock) -> None:
    spec = clock.definition
    if (
        spec.clock_id != "horvath-2013"
        or spec.transform.id != "horvath-2013-inverse"
        or spec.transform.adult_age != ADULT_AGE
        or spec.preprocessing.stage != "normalized_beta"
        or spec.feature_contract.count != 353
        or spec.coefficient_column != "CoefficientTraining"
    ):
        raise ACCError(
            "ACC_UNSUPPORTED_PROFILE", "Adapter cannot execute this clock specification."
        )


class HorvathPython:
    clock_id = "horvath-2013"
    implementation_id = "python-fsum"

    def metadata(self) -> ImplementationMetadata:
        return ImplementationMetadata(
            implementation_id=self.implementation_id,
            clock_id=self.clock_id,
            version="0.1.0",
            language="Python",
            source="aging_clock_conformance.adapters.horvath_2013",
            source_sha256=sha256_file(Path(__file__)),
            algorithm_revision="horvath-score-v1-fsum",
            stage="normalized_beta",
            deterministic=True,
            execution_mode="executed",
            runtime=f"Python {platform.python_version()}; IEEE 754 binary64, math.fsum",
        )

    def score(self, clock: Clock, sample: Sample) -> ScoreResult:
        _check_profile(clock)
        values = validated_values(clock, sample)
        score = math.fsum(
            [
                clock.definition.intercept,
                *(weight * values[feature] for feature, weight in clock.coefficients),
            ]
        )
        return ScoreResult(
            linear_score=score, value=inverse_age(score), unit=clock.definition.result_unit
        )


class HorvathDecimal:
    clock_id = "horvath-2013"
    implementation_id = "python-decimal"

    def metadata(self) -> ImplementationMetadata:
        return ImplementationMetadata(
            implementation_id=self.implementation_id,
            clock_id=self.clock_id,
            version="0.1.0",
            language="Python",
            source="aging_clock_conformance.adapters.horvath_2013",
            source_sha256=sha256_file(Path(__file__)),
            algorithm_revision="horvath-score-v1-decimal50",
            stage="normalized_beta",
            deterministic=True,
            execution_mode="executed",
            runtime=f"Python {platform.python_version()}; Decimal 50 digits, ROUND_HALF_EVEN",
        )

    def score(self, clock: Clock, sample: Sample) -> ScoreResult:
        _check_profile(clock)
        values = validated_values(clock, sample)
        with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
            score = Decimal.from_float(clock.definition.intercept)
            for feature, weight in clock.coefficients:
                score += Decimal.from_float(weight) * Decimal.from_float(values[feature])
            age = (
                Decimal(21) * score.exp() - Decimal(1)
                if score < 0
                else Decimal(21) * score + Decimal(20)
            )
        return ScoreResult(
            linear_score=float(score), value=float(age), unit=clock.definition.result_unit
        )
