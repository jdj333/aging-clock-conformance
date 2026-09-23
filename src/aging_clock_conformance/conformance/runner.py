"""Fresh score-stage conformance, never copied from upstream status flags."""

from __future__ import annotations

from ..adapters import get_adapter
from ..adapters.base import ClockAdapter
from ..errors import ACCError
from ..models import ConformanceCase, ConformanceReport, Finding, Severity
from ..registry import Clock
from ..validation import validate
from .fixtures import load_fixture


def run_conformance(
    clock: Clock, implementation: str | ClockAdapter = "python-fsum"
) -> ConformanceReport:
    adapter = (
        get_adapter(clock, implementation) if isinstance(implementation, str) else implementation
    )
    metadata = adapter.metadata()
    if (
        metadata.clock_id != clock.definition.clock_id
        or metadata.stage != clock.definition.preprocessing.stage
    ):
        raise ACCError("ACC_UNSUPPORTED_PROFILE", "Implementation and fixture stages differ.")
    fixture = load_fixture(clock)
    tolerance = fixture.suite.tolerance
    cases = []
    for case in fixture.cases:
        validation = validate(clock, case.sample)
        findings = []
        result = None
        if validation.applicability.status != case.expected_status:
            findings.append(
                Finding(
                    code="ACC_FIXTURE_STATUS_MISMATCH",
                    severity=Severity.ERROR,
                    category="implementation",
                    message="Fixture applicability differs from its expected status.",
                )
            )
        if validation.applicability.can_compute:
            try:
                result = adapter.score(clock, case.sample)
            except ACCError as error:
                findings.append(
                    Finding(
                        code=error.code,
                        severity=Severity.ERROR,
                        category="implementation",
                        message=str(error),
                    )
                )
        else:
            findings.extend(validation.applicability.reasons)
        score_difference = abs(result.linear_score - case.expected.linear_score) if result else None
        difference = abs(result.value - case.expected.value) if result else None
        relative = (
            difference / abs(case.expected.value)
            if difference is not None and case.expected.value
            else None
        )
        rounded = bool(
            result
            and (
                case.publisher_rounded_age is None
                or float(f"{result.value:.{case.significant_digits}g}")
                == case.publisher_rounded_age
            )
        )
        passed = bool(
            result
            and not findings
            and score_difference is not None
            and difference is not None
            and score_difference <= tolerance.linear_score_absolute
            and difference <= tolerance.result_absolute
            and rounded
            and result.unit == case.expected.unit
        )
        if not passed and not findings:
            findings.append(
                Finding(
                    code="ACC_REFERENCE_MISMATCH",
                    severity=Severity.ERROR,
                    category="implementation",
                    message="Implementation output differs from reference expectations.",
                )
            )
        cases.append(
            ConformanceCase(
                sample_id=case.sample.sample_id,
                passed=passed,
                expected=case.expected,
                observed=result,
                linear_score_difference=score_difference,
                absolute_difference=difference,
                relative_difference=relative,
                publisher_rounded_match=rounded,
                findings=tuple(findings),
            )
        )
    passed_count = sum(case.passed for case in cases)
    return ConformanceReport(
        clock_id=clock.definition.clock_id,
        fixture_id=fixture.suite.fixture_id,
        fixture_version=fixture.suite.version,
        profile=fixture.suite.profile,
        status="REFERENCE_CONFORMANT" if passed_count == len(cases) else "NONCONFORMANT",
        implementation=metadata,
        reference_implementation=fixture.suite.reference_implementation,
        passed=passed_count,
        failed=len(cases) - passed_count,
        tolerance=tolerance,
        cases=tuple(cases),
    )
