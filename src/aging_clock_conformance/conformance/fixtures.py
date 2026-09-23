"""Read frozen fixtures and independently produced expected values with exact hashes."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from pydantic import ValidationError

from ..errors import ACCError
from ..inputs import sample_from_bytes
from ..models import FixtureSuite, Sample, ScoreResult
from ..registry import Clock
from ..serialization import parse_document


@dataclass(frozen=True)
class FixtureCase:
    sample: Sample
    expected: ScoreResult
    publisher_rounded_age: float | None
    significant_digits: int | None
    expected_status: str


@dataclass(frozen=True)
class Fixture:
    suite: FixtureSuite
    cases: tuple[FixtureCase, ...]


def load_fixture(clock: Clock) -> Fixture:
    try:
        suite = FixtureSuite.model_validate(
            parse_document(clock.artifact_bytes(clock.definition.fixture_manifest))
        )
    except ValidationError as error:
        raise ACCError(
            "ACC_INVALID_FIXTURE", "Fixture manifest failed schema validation."
        ) from error
    if (
        suite.clock_id != clock.definition.clock_id
        or suite.stage != clock.definition.preprocessing.stage
    ):
        raise ACCError(
            "ACC_INVALID_FIXTURE", "Fixture and clock pipeline stages or identifiers differ."
        )
    source_ids = {source.id for source in (*clock.definition.sources, *suite.provenance)}
    for artifact in (suite.input, suite.expected, *suite.supporting_artifacts):
        if artifact.source_id not in source_ids:
            raise ACCError("ACC_INVALID_FIXTURE", "Fixture artifact lacks a declared source.")
        clock.artifact_bytes(artifact)
    if suite.tolerance.source_id not in source_ids:
        raise ACCError("ACC_INVALID_FIXTURE", "Tolerance lacks a source.")
    raw_input = clock.artifact_bytes(suite.input)
    raw_expected = clock.artifact_bytes(suite.expected)
    try:
        reader = csv.DictReader(io.StringIO(raw_expected.decode("utf-8-sig")), strict=True)
        columns = suite.expected_columns
        column_names = [columns.sample_id, columns.linear_score, columns.result]
        if columns.publisher_rounded:
            column_names.append(columns.publisher_rounded)
        if reader.fieldnames != column_names:
            raise ValueError("Expected output columns differ")
        expected_rows = list(reader)
        if [row[columns.sample_id] for row in expected_rows] != [
            case.sample_id for case in suite.samples
        ]:
            raise ValueError("Reference samples differ")
        cases = []
        for metadata, row in zip(suite.samples, expected_rows, strict=True):
            expected = ScoreResult(
                linear_score=float(row[columns.linear_score]),
                value=float(row[columns.result]),
                unit=clock.definition.result_unit,
            )
            rounded = float(row[columns.publisher_rounded]) if columns.publisher_rounded else None
            if (
                rounded is not None
                and float(f"{expected.value:.{columns.significant_digits}g}") != rounded
            ):
                raise ValueError("Reference does not reproduce published rounded output")
            sample = sample_from_bytes(raw_input, manifest=metadata.metadata, input_format="matrix")
            if tuple(row.feature_id for row in sample.measurements) != clock.required_features:
                raise ValueError("Fixture feature order differs from publisher model order")
            cases.append(
                FixtureCase(
                    sample, expected, rounded, columns.significant_digits, metadata.expected_status
                )
            )
    except (ValueError, TypeError, KeyError, csv.Error, UnicodeError) as error:
        raise ACCError(
            "ACC_INVALID_FIXTURE", "Reference fixture is malformed or inconsistent."
        ) from error
    return Fixture(suite, tuple(cases))
