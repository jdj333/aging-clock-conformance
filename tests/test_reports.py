import json

import pytest
from jsonschema import Draft202012Validator

from aging_clock_conformance import conformance_report, inspect_sample, score_sample
from aging_clock_conformance.models import RunReport
from aging_clock_conformance.reports import report_markdown
from aging_clock_conformance.serialization import canonical_json, sha256_bytes

from .conftest import ROOT


def test_canonical_json_and_hash():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})
    assert (
        sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    with pytest.raises(ValueError):
        canonical_json({"invalid": float("nan")})


def test_reports_round_trip_and_json_schema(clock, sample):
    schema = json.loads((ROOT / "schemas/run-report.schema.json").read_text())
    report = score_sample(clock=clock, sample=sample)
    document = json.loads(canonical_json(report))
    Draft202012Validator(schema).validate(document)
    assert RunReport.model_validate(document) == report
    assert report.provenance.python_version
    assert report.provenance.reference_checksums
    assert report.provenance.project_version == "0.1.0"
    assert "aging-clock-conformance" in report.provenance.package_versions


def test_content_id_excludes_only_timestamp(clock, sample):
    first = inspect_sample(clock=clock, sample=sample)
    second = inspect_sample(clock=clock, sample=sample)
    assert first.run_id == second.run_id
    assert first.provenance.execution_timestamp != second.provenance.execution_timestamp
    a = first.model_dump(mode="json")
    b = second.model_dump(mode="json")
    del a["provenance"]["execution_timestamp"]
    del b["provenance"]["execution_timestamp"]
    assert a == b


def test_report_contains_no_raw_measurement_values(clock, sample):
    report = inspect_sample(clock=clock, sample=sample)
    serialized = canonical_json(report)
    assert str(sample.measurements[0].value) not in serialized
    assert str(ROOT) not in serialized
    assert '"measurements"' not in serialized
    assert "hostname" not in serialized


def test_markdown_export(clock):
    text = report_markdown(conformance_report(clock))
    assert "16 passed, 0 failed" in text
    assert "clinical validity" in text


def test_failed_score_has_no_prediction(clock, sample):
    report = score_sample(clock=clock, sample=sample.model_copy(update={"manifest": None}))
    document = json.loads(canonical_json(report))
    assert document["result"] is None
    assert not document["input_validation"]["applicability"]["can_compute"]
    assert document["conformance"] is None
