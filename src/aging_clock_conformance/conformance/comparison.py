"""Compare executed implementations with each other and with frozen R evidence."""

from itertools import combinations

from ..adapters.base import ClockAdapter
from ..errors import ACCError
from ..models import ComparisonCase, ComparisonReport
from ..registry import Clock
from .runner import run_conformance


def compare_implementations(
    clock: Clock,
    implementations: tuple[str | ClockAdapter, ...] = ("python-fsum", "python-decimal"),
) -> ComparisonReport:
    if len(implementations) < 2:
        raise ACCError(
            "ACC_COMPARISON_CONFIG", "Comparison requires at least two distinct implementations."
        )
    runs = tuple(run_conformance(clock, impl) for impl in implementations)
    ids = [run.implementation.implementation_id for run in runs]
    if len(set(ids)) != len(ids):
        raise ACCError("ACC_COMPARISON_CONFIG", "Implementation identifiers must be distinct.")
    cases = []
    for index, reference in enumerate(runs[0].cases):
        results = {run.implementation.implementation_id: run.cases[index].observed for run in runs}
        complete = all(result is not None for result in results.values())
        differences = [
            abs(a.value - b.value)
            for a, b in combinations(
                [result for result in results.values() if result is not None], 2
            )
        ]
        difference = max(differences) if complete and differences else None
        relative = (
            difference / abs(reference.expected.value)
            if difference is not None and reference.expected.value
            else None
        )
        score_differences = [
            abs(a.linear_score - b.linear_score)
            for a, b in combinations(
                [result for result in results.values() if result is not None], 2
            )
        ]
        passed = (
            all(run.cases[index].passed for run in runs)
            and difference is not None
            and difference <= runs[0].tolerance.result_absolute
            and max(score_differences, default=float("inf"))
            <= runs[0].tolerance.linear_score_absolute
        )
        cases.append(
            ComparisonCase(
                sample_id=reference.sample_id,
                expected=reference.expected,
                results=results,
                absolute_difference=difference,
                relative_difference=relative,
                passed=passed,
            )
        )
    return ComparisonReport(
        clock_id=clock.definition.clock_id,
        fixture_id=runs[0].fixture_id,
        profile=runs[0].profile,
        passed=all(case.passed for case in cases),
        tolerance=runs[0].tolerance,
        runs=runs,
        cases=tuple(cases),
    )
