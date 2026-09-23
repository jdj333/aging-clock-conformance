import json
import re
import subprocess
import sys
from pathlib import Path

from aging_clock_conformance import Registry, score_sample

from .conftest import ROOT


def test_documentation_local_links_exist():
    paths = [*ROOT.glob("*.md"), *ROOT.glob("docs/*.md"), *ROOT.glob("examples/*.md")]
    for path in paths:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in link or link.startswith("#"):
                continue
            target = link.split("#", 1)[0]
            assert (path.parent / target).exists(), f"Broken link in {path.name}: {target}"


def test_exported_quickstart_sample_runs_and_refuses_overwrite(tmp_path):
    output = tmp_path / "public"
    command = [
        sys.executable,
        str(ROOT / "examples/export_public_fixture.py"),
        "--output",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    report = score_sample(
        clock=Registry.load_default().get("horvath-2013"),
        sample=output / "sample.csv",
        manifest=output / "sample.json",
    )
    assert report.result is not None and report.conformance.passed == 16
    provenance = json.loads((output / "provenance.json").read_text())
    assert provenance["license"] == "CC-BY-2.0"
    assert provenance["export_sha256"] == report.provenance.input_sha256
    again = subprocess.run(command, capture_output=True, text=True, check=False)
    assert again.returncode != 0
    assert len(list(Path(output).iterdir())) == 3


def test_packaged_and_importer_provenance_catalogs_are_identical():
    data = Registry.load_default().root
    assert (data / "public-artifacts.json").read_bytes() == (
        ROOT / "scripts/reference-imports.json"
    ).read_bytes()
