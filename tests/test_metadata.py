from dataclasses import replace

import pytest
from pydantic import ValidationError

from aging_clock_conformance import SampleManifest, score_sample, validate_sample
from aging_clock_conformance.models import Preprocessing

from .conftest import rebind


@pytest.mark.parametrize("field", ["modality", "species", "tissue", "sample_type", "unit"])
def test_metadata_gaps_block_at_full_coverage(clock, sample, field):
    metadata = sample.manifest.model_copy(update={field: None})
    report = validate_sample(clock=clock, sample=rebind(sample, manifest=metadata))
    assert report.coverage.usable_coverage_percentage == 100.0
    assert report.applicability.status == "INSUFFICIENT_METADATA"
    assert not report.applicability.can_compute


@pytest.mark.parametrize(
    "field,value",
    [
        ("modality", "proteomics"),
        ("species", "Mus musculus"),
        ("tissue", "sperm"),
        ("sample_type", "RNA"),
        ("unit", "percent"),
    ],
)
def test_incompatible_metadata(clock, sample, field, value):
    metadata = sample.manifest.model_copy(update={field: value})
    report = validate_sample(clock=clock, sample=rebind(sample, manifest=metadata))
    assert report.applicability.status == "NOT_APPLICABLE"
    assert not report.applicability.can_compute


@pytest.mark.parametrize("field", ["stage", "normalization", "reference_sha256", "evidence"])
def test_preprocessing_gaps_never_verified(clock, sample, field):
    prep = sample.manifest.preprocessing.model_copy(update={field: None})
    metadata = sample.manifest.model_copy(update={"preprocessing": prep})
    report = score_sample(clock=clock, sample=rebind(sample, manifest=metadata))
    assert report.input_validation.dimensions.preprocessing_compatibility == "UNKNOWN"
    assert report.result is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("stage", "raw_idat"),
        ("normalization", "quantile"),
        ("reference_sha256", "0" * 64),
    ],
)
def test_preprocessing_mismatch(clock, sample, field, value):
    metadata = sample.manifest.model_copy(
        update={"preprocessing": sample.manifest.preprocessing.model_copy(update={field: value})}
    )
    report = validate_sample(clock=clock, sample=rebind(sample, manifest=metadata))
    assert report.dimensions.preprocessing_compatibility == "INCOMPATIBLE"
    assert not report.applicability.can_compute


@pytest.mark.parametrize("platform", [None, "illumina_epic", "illumina_epic_v2", "targeted_panel"])
def test_platform_not_inferred_from_cpgs(clock, sample, platform):
    metadata = sample.manifest.model_copy(
        update={"assay": sample.manifest.assay.model_copy(update={"platform": platform})}
    )
    report = validate_sample(clock=clock, sample=rebind(sample, manifest=metadata))
    assert report.coverage.coverage_percentage == 100
    assert not report.applicability.can_compute


def test_accepted_metadata_remains_declared(clock, sample):
    report = validate_sample(clock=clock, sample=sample)
    assert report.applicability.status == "CONDITIONALLY_APPLICABLE"
    assert report.applicability.can_compute
    assert report.dimensions.preprocessing_compatibility == "DECLARED_COMPATIBLE"
    assert report.dimensions.reference_conformance == "NOT_RUN"
    assert report.dimensions.external_validation == "NOT_ASSESSED"
    assert report.dimensions.clinical_validity == "NOT_ESTABLISHED"


def test_no_manifest_does_not_become_normalized(clock, sample):
    report = validate_sample(clock=clock, sample=sample.model_copy(update={"manifest": None}))
    assert report.applicability.status == "INSUFFICIENT_METADATA"
    assert report.dimensions.feature_coverage == "COMPLETE"


def test_unknown_genome_build_policy(clock, sample):
    assert sample.manifest.genome_build is None
    report = validate_sample(clock=clock, sample=sample)
    assert report.applicability.can_compute
    requiring = replace(
        clock, definition=clock.definition.model_copy(update={"genome_build_required": True})
    )
    assert not validate_sample(clock=requiring, sample=sample).applicability.can_compute


def test_checksum_binding_required(clock, sample):
    metadata = sample.manifest.model_copy(update={"measurements_sha256": None})
    report = validate_sample(clock=clock, sample=sample.model_copy(update={"manifest": metadata}))
    assert "ACC_PREPROCESSING_UNBOUND" in {f.code for f in report.findings}
    assert not report.applicability.can_compute


def test_unknown_missing_policy_is_unsupported(clock, sample):
    policy = clock.definition.missing_data.model_copy(update={"policy": "unsupported"})
    changed = replace(
        clock, definition=clock.definition.model_copy(update={"missing_data": policy})
    )
    assert validate_sample(clock=changed, sample=sample).applicability.status == "UNSUPPORTED"


def test_unknown_implementation_is_unsupported(clock, sample):
    changed = replace(
        clock,
        definition=clock.definition.model_copy(update={"implementation_ids": ("unavailable",)}),
    )
    assert validate_sample(clock=changed, sample=sample).applicability.status == "UNSUPPORTED"


@pytest.mark.parametrize(
    "data",
    [
        {"sample_id": 123},
        {"sample_id": "x", "typo": True},
        {"sample_id": "x", "preprocessing": {"verified": True}},
        {"sample_id": "x", "measurements_sha256": "abc"},
    ],
)
def test_manifest_schema_strictness(data):
    with pytest.raises(ValidationError):
        SampleManifest.model_validate(data)


def test_no_preprocessing_boolean_shortcut():
    with pytest.raises(ValidationError):
        Preprocessing(normalization=True)


@pytest.mark.parametrize("evidence", ["unknown", "unresolved", "not_documented", "n/a"])
def test_placeholder_normalization_evidence_is_not_provenance(clock, sample, evidence):
    prep = sample.manifest.preprocessing.model_copy(update={"evidence": evidence})
    metadata = sample.manifest.model_copy(update={"preprocessing": prep})
    report = validate_sample(clock=clock, sample=rebind(sample, manifest=metadata))
    assert not report.applicability.can_compute
    assert report.dimensions.preprocessing_compatibility == "UNKNOWN"


def test_whitespace_only_metadata_rejected():
    with pytest.raises(ValidationError):
        Preprocessing(evidence="   ")
