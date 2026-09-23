import random
import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from decimal import ROUND_DOWN, localcontext
from io import BytesIO
from zipfile import ZipFile

import pytest

from aging_clock_conformance import (
    Measurement,
    compare_implementations,
    run_conformance,
    score_sample,
    validate_sample,
)
from aging_clock_conformance.adapters import get_adapter
from aging_clock_conformance.adapters.horvath_2013 import HorvathPython, inverse_age
from aging_clock_conformance.errors import ACCError
from aging_clock_conformance.models import ScoreResult

from .conftest import rebind

pytestmark = pytest.mark.conformance


@pytest.mark.parametrize("implementation", ["python-fsum", "python-decimal"])
def test_independent_r_golden_results(clock, fixture, implementation):
    report = run_conformance(clock, implementation)
    assert report.status == "REFERENCE_CONFORMANT"
    assert report.passed == len(fixture.cases) == 16
    assert report.failed == 0
    assert report.profile == "score-v1"
    assert report.reference_implementation.execution_mode == "recorded"
    assert report.implementation.execution_mode == "executed"
    assert all(case.publisher_rounded_match for case in report.cases)
    assert max(c.absolute_difference for c in report.cases) < 1e-10
    assert max(c.linear_score_difference for c in report.cases) < 1e-12


def test_live_implementations_agree(clock):
    report = compare_implementations(clock)
    assert report.passed
    assert len(report.cases) == 16 and len(report.runs) == 2
    assert all(c.absolute_difference <= report.tolerance.result_absolute for c in report.cases)


@pytest.mark.parametrize("score,expected", [(-1.0, 6.725468264600289), (0.0, 20.0), (1.0, 41.0)])
def test_inverse_transform_branches(score, expected):
    # Analytic boundary/branch examples, separate from empirical reference fixtures.
    assert inverse_age(score) == pytest.approx(expected, abs=1e-14)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -float("inf")])
def test_transform_nonfinite_rejected(score):
    with pytest.raises(ACCError):
        inverse_age(score)


def test_transform_adult_age_cannot_drift():
    with pytest.raises(ACCError):
        inverse_age(1.0, adult_age=21.0)


@pytest.mark.parametrize("implementation", ["python-fsum", "python-decimal"])
def test_ordering_extras_and_repeatability(clock, sample, implementation):
    adapter = get_adapter(clock, implementation)
    baseline = adapter.score(clock, sample)
    for seed in range(10):
        rows = list(sample.measurements)
        random.Random(seed).shuffle(rows)
        rows.append(Measurement(feature_id="cg99999999", value="0.5", unit="beta_fraction"))
        modified = rebind(sample, measurements=rows)
        assert adapter.score(clock, modified) == baseline
        assert validate_sample(clock=clock, sample=modified).coverage.extra_count == 1
    assert adapter.score(clock, sample) == baseline


def test_decimal_context_does_not_change_results(clock, sample):
    adapter = get_adapter(clock, "python-decimal")
    baseline = adapter.score(clock, sample)
    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_DOWN
        assert adapter.score(clock, sample) == baseline


class WrongTransform(HorvathPython):
    implementation_id = "deliberately-wrong-test-adapter"

    def score(self, clock, sample):
        result = super().score(clock, sample)
        return ScoreResult(
            linear_score=result.linear_score, value=result.value + 1.0, unit=result.unit
        )


def test_altered_implementation_fails(clock):
    report = run_conformance(clock, WrongTransform())
    assert report.status == "NONCONFORMANT" and report.failed == 16
    assert all("ACC_REFERENCE_MISMATCH" in {f.code for f in c.findings} for c in report.cases)
    assert not compare_implementations(clock, (HorvathPython(), WrongTransform())).passed


def test_two_equally_wrong_implementations_cannot_pass(clock):
    class AnotherWrongTransform(WrongTransform):
        implementation_id = "another-wrong-test-adapter"

    report = compare_implementations(clock, (WrongTransform(), AnotherWrongTransform()))
    assert all(case.absolute_difference == 0.0 for case in report.cases)
    assert not report.passed


def test_rounded_reference_values_match_actual_publisher_document(clock, fixture):
    tutorial = next(a for a in fixture.suite.supporting_artifacts if a.role == "publisher_tutorial")
    with ZipFile(BytesIO(clock.artifact_bytes(tutorial))) as archive:
        text = " ".join(ET.fromstring(archive.read("word/document.xml")).itertext())
    match = re.search(r"signif\s*\(\s*datout\$DNAmAge\s*,\s*2\s*\)\s*\[1\]\s*([\d.\s]+)", text)
    assert match is not None
    observed = tuple(float(value) for value in match.group(1).split())
    assert observed == tuple(case.publisher_rounded_age for case in fixture.cases)


def test_scoring_abstains_if_current_implementation_fails_reference(clock, sample, monkeypatch):
    monkeypatch.setattr("aging_clock_conformance.api.get_adapter", lambda *args: WrongTransform())
    report = score_sample(clock=clock, sample=sample)
    assert report.result is None
    assert not report.input_validation.applicability.can_compute
    assert report.input_validation.dimensions.reference_conformance == "NONCONFORMANT"
    assert report.input_validation.dimensions.computational_applicability == "NOT_APPLICABLE"


def test_in_memory_coefficient_tampering_cannot_skip_integrity(clock, sample):
    altered = replace(
        clock, coefficients=((clock.coefficients[0][0], 0.0), *clock.coefficients[1:])
    )
    with pytest.raises(ACCError) as error:
        get_adapter(clock).score(altered, sample)
    assert error.value.code == "ACC_INVALID_COEFFICIENTS"


@pytest.mark.parametrize("implementations", [("python-fsum",), ("python-fsum", "python-fsum")])
def test_comparison_requires_distinct_paths(clock, implementations):
    with pytest.raises(ACCError) as error:
        compare_implementations(clock, implementations)
    assert error.value.code == "ACC_COMPARISON_CONFIG"


def test_full_lifecycle(clock, sample):
    report = score_sample(clock=clock, sample=sample)
    assert report.result is not None
    assert report.result.value == pytest.approx(60.2774909978736, abs=1e-10)
    assert report.conformance.passed == 16
    assert report.provenance.input_sha256 == sample.input_sha256
    assert report.input_validation.dimensions.reference_conformance == "REFERENCE_CONFORMANT"
    assert report.input_validation.dimensions.clinical_validity == "NOT_ESTABLISHED"
