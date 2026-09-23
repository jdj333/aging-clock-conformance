import math

import pytest
from pydantic import ValidationError

from aging_clock_conformance import Measurement, score_sample, validate_sample
from aging_clock_conformance.adapters import get_adapter
from aging_clock_conformance.errors import ComputationBlocked
from aging_clock_conformance.validation.values import parse_value

from .conftest import rebind


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (None, "ACC_NULL_VALUE"),
        ("", "ACC_NULL_VALUE"),
        ("NA", "ACC_NULL_VALUE"),
        ("n/a", "ACC_NULL_VALUE"),
        ("null", "ACC_NULL_VALUE"),
        ("None", "ACC_NULL_VALUE"),
        ("NaN", "ACC_NONFINITE_VALUE"),
        (float("nan"), "ACC_NONFINITE_VALUE"),
        (float("inf"), "ACC_NONFINITE_VALUE"),
        (-float("inf"), "ACC_NONFINITE_VALUE"),
        ("+Infinity", "ACC_NONFINITE_VALUE"),
        ("-inf", "ACC_NONFINITE_VALUE"),
        ("1e999", "ACC_NONFINITE_VALUE"),
        ("1e-999", "ACC_NUMERIC_UNDERFLOW"),
        ("beta", "ACC_NONNUMERIC_VALUE"),
        ("true", "ACC_NONNUMERIC_VALUE"),
        ("1_0", "ACC_NONNUMERIC_VALUE"),
        ("0,5", "ACC_NONNUMERIC_VALUE"),
        ("０.５", "ACC_NONNUMERIC_VALUE"),
        (-0.001, "ACC_VALUE_OUT_OF_RANGE"),
        (1.001, "ACC_VALUE_OUT_OF_RANGE"),
    ],
)
def test_bad_values_block_every_scoring_route(clock, sample, value, code):
    bad_row = sample.measurements[0].model_copy(update={"value": value})
    bad = rebind(sample, measurements=(bad_row, *sample.measurements[1:]))
    report = validate_sample(clock=clock, sample=bad)
    assert code in {finding.code for finding in report.findings}
    assert report.coverage.present_count == 353
    assert report.coverage.valid_numeric_count == 352
    assert report.coverage.invalid_count == 1
    assert not report.applicability.can_compute
    assert score_sample(clock=clock, sample=bad).result is None
    for name in clock.definition.implementation_ids:
        with pytest.raises(ComputationBlocked):
            get_adapter(clock, name).score(clock, bad)


@pytest.mark.parametrize("value", [0.0, 1.0, "-0", "+0.5", "5e-1", ".5", " 0.5 ", "1."])
def test_numeric_boundaries(value):
    number, error = parse_value(value)
    assert error is None and math.isfinite(number)


@pytest.mark.parametrize(
    "identifier",
    [None, "", "CG00000000", "cg1", "cg000000000", " cg00000000", "cg００００００００"],
)
def test_bad_identifiers(clock, sample, identifier):
    bad = rebind(
        sample,
        measurements=(Measurement(feature_id=identifier, value=0.5), *sample.measurements[1:]),
    )
    report = validate_sample(clock=clock, sample=bad)
    codes = {f.code for f in report.findings}
    assert codes & {"ACC_FEATURE_ID_MISSING", "ACC_MALFORMED_IDENTIFIER"}
    assert report.coverage.missing_count == 1
    assert not report.applicability.can_compute


@pytest.mark.parametrize("value", [True, False, [], {}])
def test_measurement_schema_rejects_silent_scalar_coercion(value):
    with pytest.raises(ValidationError):
        Measurement(feature_id="cg00000000", value=value)


@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicates_never_overwrite(clock, sample, conflicting):
    original = sample.measurements[0]
    duplicate = original.model_copy(update={"value": "0.999"}) if conflicting else original
    bad = rebind(sample, measurements=(*sample.measurements, duplicate))
    report = validate_sample(clock=clock, sample=bad)
    code = "ACC_CONFLICTING_DUPLICATE" if conflicting else "ACC_DUPLICATE_FEATURE"
    assert code in {f.code for f in report.findings}
    assert report.coverage.valid_numeric_count == 352
    assert report.coverage.present_count == 353
    assert not report.applicability.can_compute


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("unit", "percent", "ACC_UNEXPECTED_UNIT"),
        ("quality_flag", "FAIL", "ACC_QUALITY_FLAG"),
        ("quality_flag", "unknown", "ACC_QUALITY_FLAG"),
    ],
)
def test_row_annotations(clock, sample, field, value, code):
    row = sample.measurements[0].model_copy(update={field: value})
    report = validate_sample(
        clock=clock, sample=rebind(sample, measurements=(row, *sample.measurements[1:]))
    )
    assert code in {f.code for f in report.findings}
    assert not report.applicability.can_compute


def test_missing_and_null_stay_separate(clock, sample):
    rows = (sample.measurements[1].model_copy(update={"value": None}), *sample.measurements[2:])
    report = validate_sample(clock=clock, sample=rebind(sample, measurements=rows))
    assert report.coverage.missing_count == report.coverage.invalid_count == 1
    assert report.coverage.present_count == 352
    assert report.coverage.valid_numeric_count == 351
    assert set(report.coverage.missing_features).isdisjoint(report.coverage.invalid_features)


def test_near_complete_coverage_never_authorizes_computation(clock, sample):
    bad = rebind(sample, measurements=sample.measurements[1:])
    report = validate_sample(clock=clock, sample=bad)
    assert report.coverage.usable_coverage_percentage > 99.0
    assert not report.applicability.can_compute
    assert score_sample(clock=clock, sample=bad).result is None
