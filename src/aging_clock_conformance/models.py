"""Versioned contracts shared by the API, CLI, registry, and MCP boundary."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)

Text = Annotated[StrictStr, Field(min_length=1, pattern=r"\S")]
Digest = Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]
Number = StrictFloat


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Source(Model):
    id: Text
    title: Text
    author: Text
    url: Annotated[Text, Field(pattern=r"^https://")]
    doi: Text | None = None
    accessed: Annotated[Text, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    license: Text
    revision: Text | None = None
    locator: Text


class Artifact(Model):
    path: Text
    sha256: Digest
    source_id: Text
    role: Text
    transformation: Text
    derived_from: tuple[Text, ...] = ()


class Requirement(Model):
    status: Literal["DOCUMENTED", "UNKNOWN", "UNSUPPORTED"]
    accepted: tuple[Text, ...]
    source_ids: tuple[Text, ...] = Field(min_length=1)
    note: Text

    @model_validator(mode="after")
    def documented_has_values(self) -> Requirement:
        if self.status == "DOCUMENTED" and not self.accepted:
            raise ValueError("Documented requirements need explicit accepted values")
        if len(set(self.accepted)) != len(self.accepted):
            raise ValueError("Accepted values must be unique")
        return self


class PreprocessingRequirement(Model):
    stage: Text
    normalization: Text
    reference_sha256: Digest
    evidence_required: Literal[True]
    source_ids: tuple[Text, ...] = Field(min_length=1)
    note: Text


class FeatureContract(Model):
    identifier_type: Text
    identifier_pattern: Text
    count: Annotated[StrictInt, Field(gt=0)]
    unit: Text
    minimum: Number | None
    maximum: Number | None
    source_ids: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def ordered_bounds(self) -> FeatureContract:
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("Minimum must not exceed maximum")
        return self


class MissingDataPolicy(Model):
    policy: Literal["complete_required", "unsupported"]
    source_ids: tuple[Text, ...] = Field(min_length=1)
    note: Text


class Transform(Model):
    id: Text
    adult_age: Number | None
    formula: Text
    source_ids: tuple[Text, ...] = Field(min_length=1)


class ClockDefinition(Model):
    schema_version: Literal["1.0"]
    clock_id: Annotated[Text, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    name: Text
    aliases: tuple[Text, ...]
    version: Text
    publication_year: StrictInt
    publication_source_id: Text
    modality: Requirement
    species: Requirement
    tissue: Requirement
    sample_type: Requirement
    assay: Requirement
    platform: Requirement
    target: Text
    result_unit: Text
    feature_contract: FeatureContract
    coefficients: Artifact
    intercept: Number
    coefficient_column: Text
    feature_column: Text
    intercept_label: Text
    transform: Transform
    preprocessing: PreprocessingRequirement
    missing_data: MissingDataPolicy
    genome_build_required: StrictBool
    genome_build_note: Text
    sources: tuple[Source, ...] = Field(min_length=1)
    implementation_ids: tuple[Text, ...]
    fixture_manifest: Artifact
    scientific_source_ids: tuple[Text, ...] = Field(min_length=1)
    external_validation: Literal["NOT_ASSESSED"]
    clinical_validity: Literal["NOT_ESTABLISHED"]
    research_use_only: Literal[True]
    notes: tuple[Text, ...]

    @model_validator(mode="after")
    def source_integrity(self) -> ClockDefinition:
        ids = [source.id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("Source identifiers must be unique")
        referenced = [
            self.publication_source_id,
            self.coefficients.source_id,
            self.fixture_manifest.source_id,
            *self.scientific_source_ids,
        ]
        for requirement in (
            self.modality,
            self.species,
            self.tissue,
            self.sample_type,
            self.assay,
            self.platform,
            self.feature_contract,
            self.transform,
            self.preprocessing,
            self.missing_data,
        ):
            referenced.extend(requirement.source_ids)
        if set(referenced) - set(ids):
            raise ValueError("Every scientific requirement must reference a declared source")
        if len(set(self.implementation_ids)) != len(self.implementation_ids):
            raise ValueError("Implementation identifiers must be unique")
        return self


class Assay(Model):
    method: Text | None = None
    platform: Text | None = None


class Preprocessing(Model):
    stage: Text | None = None
    normalization: Text | None = None
    reference_sha256: Digest | None = None
    evidence: Text | None = None


class SampleManifest(Model):
    schema_version: Literal["1.0"] = "1.0"
    sample_id: Text
    modality: Text | None = None
    species: Text | None = None
    tissue: Text | None = None
    sample_type: Text | None = None
    assay: Assay = Field(default_factory=Assay)
    preprocessing: Preprocessing = Field(default_factory=Preprocessing)
    genome_build: Text | None = None
    unit: Text | None = None
    measurements: Text | None = None
    measurements_sha256: Digest | None = None
    input_format: Literal["long", "matrix"] = "long"


class Measurement(Model):
    # Keep malformed numeric strings and IEEE special values until validation.
    # Strict scalar types reject bool and prevent implicit string conversion.
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=True)
    feature_id: StrictStr | None
    value: StrictStr | StrictFloat | StrictInt | None
    unit: Text | None = None
    source_column: Text | None = None
    quality_flag: Text | None = None


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    BLOCKING = "BLOCKING"


class Finding(Model):
    code: Annotated[Text, Field(pattern=r"^ACC_[A-Z_]+$")]
    severity: Severity
    category: Literal["schema", "data_quality", "coverage", "metadata", "implementation"]
    message: Text
    feature_id: StrictStr | None = None
    row: StrictInt | None = None


class Sample(Model):
    sample_id: Text
    measurements: tuple[Measurement, ...]
    manifest: SampleManifest | None = None
    input_sha256: Digest
    manifest_sha256: Digest | None = None
    input_findings: tuple[Finding, ...] = ()


class ApplicabilityStatus(StrEnum):
    APPLICABLE = "APPLICABLE"
    CONDITIONALLY_APPLICABLE = "CONDITIONALLY_APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_METADATA = "INSUFFICIENT_METADATA"
    UNSUPPORTED = "UNSUPPORTED"


class Applicability(Model):
    status: ApplicabilityStatus
    can_compute: bool
    reasons: tuple[Finding, ...]
    assumptions: tuple[Text, ...] = ()


class Coverage(Model):
    required_count: StrictInt
    present_count: StrictInt
    valid_numeric_count: StrictInt
    missing_count: StrictInt
    invalid_count: StrictInt
    extra_count: StrictInt
    coverage_percentage: Number
    usable_coverage_percentage: Number
    missing_features: tuple[Text, ...]
    invalid_features: tuple[Text, ...]
    extra_features: tuple[Text, ...]


Compatibility = Literal["DECLARED_COMPATIBLE", "UNKNOWN", "INCOMPATIBLE", "UNSUPPORTED"]


class Dimensions(Model):
    schema_validity: Literal["VALID", "INVALID"]
    input_data_quality: Literal["PASS", "FAIL"]
    feature_coverage: Literal["COMPLETE", "INCOMPLETE"]
    preprocessing_compatibility: Compatibility
    assay_platform_compatibility: Compatibility
    tissue_compatibility: Compatibility
    computational_applicability: ApplicabilityStatus
    reference_conformance: Literal["NOT_RUN", "REFERENCE_CONFORMANT", "NONCONFORMANT"]
    external_validation: Literal["NOT_ASSESSED"] = "NOT_ASSESSED"
    clinical_validity: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"


class ValidationReport(Model):
    clock_id: Text
    sample_id: Text
    input_sha256: Digest
    manifest_sha256: Digest | None
    dimensions: Dimensions
    findings: tuple[Finding, ...]
    coverage: Coverage
    applicability: Applicability


class ImplementationMetadata(Model):
    implementation_id: Text
    clock_id: Text
    version: Text
    language: Text
    source: Text
    source_sha256: Digest
    algorithm_revision: Text
    stage: Text
    deterministic: Literal[True]
    execution_mode: Literal["executed", "recorded"]
    runtime: Text


class ScoreResult(Model):
    linear_score: Number
    value: Number
    unit: Text


class ExpectedSample(Model):
    sample_id: Text
    expected_status: ApplicabilityStatus
    metadata: SampleManifest


class Tolerance(Model):
    linear_score_absolute: Annotated[Number, Field(gt=0)]
    result_absolute: Annotated[Number, Field(gt=0)]
    rationale: Text
    source_id: Text


class ExpectedColumns(Model):
    sample_id: Text
    linear_score: Text
    result: Text
    publisher_rounded: Text | None = None
    significant_digits: Annotated[StrictInt, Field(ge=1, le=17)] | None = None

    @model_validator(mode="after")
    def paired_rounding(self) -> ExpectedColumns:
        if (self.publisher_rounded is None) != (self.significant_digits is None):
            raise ValueError("Publisher rounding column and significant digits must be paired")
        names = [self.sample_id, self.linear_score, self.result]
        if self.publisher_rounded:
            names.append(self.publisher_rounded)
        if len(names) != len(set(names)):
            raise ValueError("Expected-output columns must be distinct")
        return self


class FixtureSuite(Model):
    schema_version: Literal["1.0"]
    fixture_id: Text
    version: Text
    clock_id: Text
    stage: Text
    profile: Text
    input_description: Text
    input: Artifact
    expected: Artifact
    expected_columns: ExpectedColumns
    supporting_artifacts: tuple[Artifact, ...]
    samples: tuple[ExpectedSample, ...] = Field(min_length=1)
    tolerance: Tolerance
    reference_implementation: ImplementationMetadata
    provenance: tuple[Source, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_samples(self) -> FixtureSuite:
        ids = [s.sample_id for s in self.samples]
        if len(ids) != len(set(ids)):
            raise ValueError("Fixture samples must be unique")
        if any(s.sample_id != s.metadata.sample_id for s in self.samples):
            raise ValueError("Fixture sample identifiers must match metadata")
        return self


class ConformanceCase(Model):
    sample_id: Text
    passed: bool
    expected: ScoreResult
    observed: ScoreResult | None
    linear_score_difference: Number | None
    absolute_difference: Number | None
    relative_difference: Number | None
    publisher_rounded_match: bool
    findings: tuple[Finding, ...] = ()


class ConformanceReport(Model):
    clock_id: Text
    fixture_id: Text
    fixture_version: Text
    profile: Text
    status: Literal["REFERENCE_CONFORMANT", "NONCONFORMANT"]
    implementation: ImplementationMetadata
    reference_implementation: ImplementationMetadata
    passed: StrictInt
    failed: StrictInt
    tolerance: Tolerance
    cases: tuple[ConformanceCase, ...]


class ComparisonCase(Model):
    sample_id: Text
    expected: ScoreResult
    results: dict[StrictStr, ScoreResult | None]
    absolute_difference: Number | None
    relative_difference: Number | None
    passed: bool


class ComparisonReport(Model):
    clock_id: Text
    fixture_id: Text
    profile: Text
    passed: bool
    tolerance: Tolerance
    runs: tuple[ConformanceReport, ...]
    cases: tuple[ComparisonCase, ...]


class Provenance(Model):
    project_version: Text
    git_commit: Text | None
    git_dirty: bool | None
    clock_version: Text
    clock_definition_sha256: Digest
    input_sha256: Digest | None
    manifest_sha256: Digest | None
    reference_checksums: dict[StrictStr, Digest]
    execution_timestamp: Text
    python_version: Text
    package_versions: dict[StrictStr, StrictStr]
    operating_system: Text
    sources: tuple[Source, ...]


class RunReport(Model):
    schema_version: Literal["1.0"] = "1.0"
    run_id: Digest
    operation: Text
    clock: ClockDefinition
    input_validation: ValidationReport | None = None
    implementation: ImplementationMetadata | None = None
    result: ScoreResult | None = None
    conformance: ConformanceReport | None = None
    comparison: ComparisonReport | None = None
    provenance: Provenance
    research_use_only: Literal[True] = True
