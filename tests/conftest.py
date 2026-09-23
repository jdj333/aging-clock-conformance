"""Tests use public reference data only; mutations are software test inputs, not cohorts."""

from pathlib import Path

import pytest

from aging_clock_conformance import Registry, inline_sample, load_fixture

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def registry():
    return Registry.load_default()


@pytest.fixture(scope="session")
def clock(registry):
    return registry.get("horvath-2013")


@pytest.fixture(scope="session")
def fixture(clock):
    return load_fixture(clock)


@pytest.fixture
def sample(fixture):
    return fixture.cases[0].sample


def rebind(sample, *, measurements=None, manifest=None):
    """Explicitly declare modified test rows against their canonical checksum."""
    metadata = manifest if manifest is not None else sample.manifest
    rows = measurements if measurements is not None else sample.measurements
    metadata = metadata.model_copy(update={"measurements": None, "measurements_sha256": None})
    first = inline_sample(tuple(rows), metadata)
    return inline_sample(
        tuple(rows), metadata.model_copy(update={"measurements_sha256": first.input_sha256})
    )
