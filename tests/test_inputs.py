import json

import pytest

from aging_clock_conformance import load_sample, validate_sample
from aging_clock_conformance.errors import ACCError
from aging_clock_conformance.inputs import inline_sample, parse_manifest, sample_from_bytes
from aging_clock_conformance.serialization import canonical_json, parse_document, sha256_bytes


@pytest.mark.parametrize(
    "raw,code",
    [
        (b"", "ACC_EMPTY_INPUT"),
        (b"feature_id,value\n", "ACC_EMPTY_INPUT"),
        (b"feature_id,value,value\ncg00000000,.5,.5\n", "ACC_DUPLICATE_HEADER"),
        (b"feature_id,value\ncg00000000,.5,extra\n", "ACC_ROW_WIDTH"),
        (b"feature_id,value\ncg00000000\n", "ACC_ROW_WIDTH"),
        (b"feature_id,value\n\n", "ACC_ROW_WIDTH"),
        (b"feature_id,value\n\xff,.5\n", "ACC_MALFORMED_CSV"),
        (b'feature_id,value\n"unterminated,.5\n', "ACC_MALFORMED_CSV"),
        (b"feature_id,beta\ncg00000000,.5\n", "ACC_CSV_COLUMNS"),
        (b"sample_id,cg00000000\nx,.5\ny,.6\n", "ACC_CSV_COLUMNS"),
    ],
)
def test_structural_rejections(raw, code):
    with pytest.raises(ACCError) as error:
        sample_from_bytes(raw)
    assert error.value.code == code


def test_long_sample_selection():
    raw = b"sample_id,feature_id,value\na,cg00000000,.1\nb,cg00000000,.2\n"
    with pytest.raises(ACCError, match="Select one sample"):
        sample_from_bytes(raw)
    result = sample_from_bytes(raw, sample_id="b")
    assert len(result.measurements) == 1 and result.measurements[0].value == ".2"
    with pytest.raises(ACCError) as error:
        sample_from_bytes(raw, sample_id="missing")
    assert error.value.code == "ACC_UNKNOWN_SAMPLE"


def test_matrix_sample_selection():
    raw = b"probe_id,a,b\ncg00000000,.1,.2\n"
    with pytest.raises(ACCError) as error:
        sample_from_bytes(raw, input_format="matrix")
    assert error.value.code == "ACC_SAMPLE_SELECTION_REQUIRED"
    assert (
        sample_from_bytes(raw, input_format="matrix", sample_id="b").measurements[0].value == ".2"
    )


def test_missing_sample_id():
    with pytest.raises(ACCError) as error:
        sample_from_bytes(b"sample_id,feature_id,value\n,cg00000000,.1\n")
    assert error.value.code == "ACC_SAMPLE_ID_MISSING"


def test_duplicate_rows_are_preserved_for_validation(clock):
    raw = b"feature_id,value\ncg00000000,.1\ncg00000000,.2\n"
    sample = sample_from_bytes(raw)
    assert len(sample.measurements) == 2
    assert "ACC_CONFLICTING_DUPLICATE" in {
        f.code for f in validate_sample(clock=clock, sample=sample).findings
    }


def test_manifest_binding_and_relative_paths(tmp_path, clock, sample, fixture):
    raw = clock.artifact_bytes(fixture.suite.input)
    path = tmp_path / "matrix.csv"
    path.write_bytes(raw)
    metadata = sample.manifest.model_copy(update={"measurements": "matrix.csv"})
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(canonical_json(metadata))
    loaded = load_sample(path, manifest=manifest_path)
    assert loaded.input_sha256 == sha256_bytes(raw)
    assert loaded.manifest_sha256 == sha256_bytes(manifest_path.read_bytes())
    assert validate_sample(clock=clock, sample=loaded).applicability.can_compute
    path.write_bytes(raw + b"\n")
    with pytest.raises(ACCError):
        load_sample(path, manifest=manifest_path)
    path.write_bytes(raw.replace(b"GSM946048", b"GSM946099"))
    with pytest.raises(ACCError):
        load_sample(path, manifest=manifest_path)


def test_manifest_checksum_mismatch_is_visible(clock, sample, fixture):
    metadata = sample.manifest.model_copy(update={"measurements_sha256": "0" * 64})
    loaded = sample_from_bytes(
        clock.artifact_bytes(fixture.suite.input), manifest=metadata, input_format="matrix"
    )
    report = validate_sample(clock=clock, sample=loaded)
    assert report.dimensions.schema_validity == "INVALID"
    assert "ACC_INPUT_CHECKSUM_MISMATCH" in {f.code for f in report.findings}


def test_manifest_cannot_name_a_different_file(tmp_path, sample):
    metadata = sample.manifest.model_copy(update={"measurements": "different.csv"})
    manifest = tmp_path / "sample.json"
    manifest.write_text(canonical_json(metadata))
    with pytest.raises(ACCError) as error:
        load_sample(tmp_path / "input.csv", manifest=manifest)
    assert error.value.code == "ACC_MANIFEST_INPUT_MISMATCH"


def test_manifest_and_explicit_sample_must_agree(sample):
    with pytest.raises(ACCError) as error:
        sample_from_bytes(
            b"feature_id,value\ncg00000000,.5\n", manifest=sample.manifest, sample_id="other"
        )
    assert error.value.code == "ACC_SAMPLE_MISMATCH"


@pytest.mark.parametrize(
    "raw,yaml_format",
    [
        (b'{"sample_id":"a","sample_id":"b"}', False),
        (b"sample_id: a\nsample_id: b\n", True),
        (b"sample_id: a\npreprocessing:\n  stage: x\n  stage: y\n", True),
    ],
)
def test_duplicate_manifest_keys_never_overwrite(raw, yaml_format):
    with pytest.raises(ACCError) as error:
        parse_manifest(raw, yaml_format=yaml_format)
    assert error.value.code == "ACC_DUPLICATE_KEY"


@pytest.mark.parametrize("raw", [b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}'])
def test_json_special_numbers_rejected(raw):
    with pytest.raises(ACCError):
        parse_document(raw)


def test_yaml_cannot_execute_objects():
    with pytest.raises(ACCError):
        parse_manifest(b"!!python/object/apply:os.system ['echo wrong']", yaml_format=True)


def test_inline_never_reads_local_paths(sample):
    metadata = sample.manifest.model_copy(update={"measurements": "/etc/passwd"})
    with pytest.raises(ACCError) as error:
        inline_sample(sample.measurements, metadata)
    assert error.value.code == "ACC_INLINE_PATH_FORBIDDEN"


def test_yaml_and_json_manifest_semantics(sample):
    # JSON is a YAML subset. Both paths must preserve all explicit nulls and strings.
    raw = canonical_json(sample.manifest).encode()
    assert parse_manifest(raw) == parse_manifest(raw, yaml_format=True)
    assert json.loads(raw)["genome_build"] is None
