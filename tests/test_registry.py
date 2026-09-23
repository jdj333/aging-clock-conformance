import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from aging_clock_conformance import Registry, load_fixture
from aging_clock_conformance.errors import ACCError
from aging_clock_conformance.models import ClockDefinition
from aging_clock_conformance.registry import load_coefficients
from aging_clock_conformance.serialization import safe_path


def test_registry_sources_and_canonical_model(clock, registry):
    assert len(registry.list()) == 1
    assert registry.get("horvath2013") == clock
    assert len(clock.required_features) == len(set(clock.required_features)) == 353
    assert clock.definition.intercept == 0.695507258
    assert clock.definition.coefficient_column == "CoefficientTraining"
    assert clock.definition.research_use_only is True


def test_unknown_clock_has_no_synthetic_support(registry):
    with pytest.raises(ACCError) as error:
        registry.get("grimage")
    assert error.value.code == "ACC_UNKNOWN_CLOCK"


@pytest.mark.parametrize("role", ["coefficients", "normalized", "expected", "manifest"])
def test_corrupted_artifact_rejected_before_computation(tmp_path, clock, fixture, role):
    root = tmp_path / "registry"
    shutil.copytree(clock.root, root)
    paths = {
        "coefficients": clock.definition.coefficients.path,
        "normalized": fixture.suite.input.path,
        "expected": fixture.suite.expected.path,
        "manifest": clock.definition.fixture_manifest.path,
    }
    path = root / paths[role]
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ACCError) as error:
        Registry(root).get("horvath-2013")
    assert error.value.code == "ACC_CHECKSUM_MISMATCH"


def test_fixture_rechecks_after_clock_was_loaded(tmp_path, clock, fixture):
    root = tmp_path / "registry"
    shutil.copytree(clock.root, root)
    loaded = Registry(root).get("horvath-2013")
    (root / fixture.suite.expected.path).write_text("corrupt")
    with pytest.raises(ACCError) as error:
        load_fixture(loaded)
    assert error.value.code == "ACC_CHECKSUM_MISMATCH"


def test_unlisted_artifact_rejected(tmp_path, clock):
    root = tmp_path / "registry"
    shutil.copytree(clock.root, root)
    (root / "untracked.txt").write_text("unexpected")
    with pytest.raises(ACCError) as error:
        Registry(root).verify_integrity()
    assert error.value.code == "ACC_REGISTRY_INVALID"


@pytest.mark.parametrize("relative", ["../secret", "/etc/passwd"])
def test_artifact_path_escape(tmp_path, relative):
    with pytest.raises(ACCError):
        safe_path(tmp_path, relative)


def test_symlink_escape(tmp_path):
    (tmp_path / "link").symlink_to("/etc/passwd")
    with pytest.raises(ACCError):
        safe_path(tmp_path, "link")


def test_scientific_facts_require_sources(clock):
    document = clock.definition.model_dump(mode="json")
    document["transform"]["source_ids"] = ["invented-source"]
    with pytest.raises(ValidationError):
        ClockDefinition.model_validate(document)


def test_registry_rejects_duplicate_source_ids(clock):
    document = clock.definition.model_dump(mode="json")
    document["sources"].append(document["sources"][0])
    with pytest.raises(ValidationError):
        ClockDefinition.model_validate(document)


@pytest.mark.parametrize("mutation", ["duplicate", "nonfinite", "intercept", "shrunken"])
def test_coefficient_contract(clock, mutation):
    raw = clock.artifact_bytes(clock.definition.coefficients)
    lines = raw.decode().splitlines()
    definition = clock.definition
    if mutation == "duplicate":
        lines[3] = lines[2]
    elif mutation == "nonfinite":
        lines[2] = lines[2].replace(lines[2].split(",")[1], "NaN", 1)
    elif mutation == "intercept":
        definition = definition.model_copy(update={"intercept": 123.0})
    else:
        definition = definition.model_copy(update={"coefficient_column": "missing_column"})
    with pytest.raises(ACCError):
        load_coefficients(definition, "\n".join(lines).encode())


def test_import_allowlist_has_no_private_material():
    root = Path(__file__).resolve().parents[1]
    plan = json.loads((root / "scripts/reference-imports.json").read_text())
    assert len(plan["artifacts"]) == 10
    assert all(
        item["upstream_path"].startswith(("data/reference/", "conformance/", "LICENSE"))
        for item in plan["artifacts"]
    )
    assert all("personal" not in item["path"].lower() for item in plan["artifacts"])
    assert not list((root / "src").rglob("*.xlsx"))
