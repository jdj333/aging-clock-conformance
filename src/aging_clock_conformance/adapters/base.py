"""Small adapter protocol; callers never supply unchecked feature dictionaries."""

from __future__ import annotations

from typing import Protocol

from ..errors import ACCError, ComputationBlocked
from ..models import ImplementationMetadata, Sample, ScoreResult
from ..registry import Clock, load_coefficients
from ..validation import validate
from ..validation.values import check_values


class ClockAdapter(Protocol):
    clock_id: str
    implementation_id: str

    def metadata(self) -> ImplementationMetadata: ...

    def score(self, clock: Clock, sample: Sample) -> ScoreResult: ...


def validated_values(clock: Clock, sample: Sample) -> dict[str, float]:
    """Recheck input gates and model bytes even when an adapter is called directly."""
    raw = clock.artifact_bytes(clock.definition.coefficients)
    if load_coefficients(clock.definition, raw) != clock.coefficients:
        raise ACCError(
            "ACC_INVALID_COEFFICIENTS", "In-memory coefficients differ from the verified artifact."
        )
    report = validate(clock, sample)
    if not report.applicability.can_compute:
        raise ComputationBlocked(report)
    checked = check_values(
        sample.measurements,
        clock.definition.feature_contract,
        sample.manifest.unit if sample.manifest else None,
    )
    return dict(checked.usable)
