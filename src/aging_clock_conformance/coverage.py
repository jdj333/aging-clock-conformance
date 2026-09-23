"""Coverage is an observation, never a permission to compute."""

from .models import Coverage
from .validation.values import CheckedValues


def feature_coverage(required_features: tuple[str, ...], checked: CheckedValues) -> Coverage:
    required = set(required_features)
    present = required & checked.present
    usable = required & {feature for feature, _ in checked.usable}
    missing = required - present
    invalid = present - usable
    extra = checked.present - required
    return Coverage(
        required_count=len(required),
        present_count=len(present),
        valid_numeric_count=len(usable),
        missing_count=len(missing),
        invalid_count=len(invalid),
        extra_count=len(extra),
        coverage_percentage=100.0 * len(present) / len(required),
        usable_coverage_percentage=100.0 * len(usable) / len(required),
        missing_features=tuple(sorted(missing)),
        invalid_features=tuple(sorted(invalid)),
        extra_features=tuple(sorted(extra)),
    )
