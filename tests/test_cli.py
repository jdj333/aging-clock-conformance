import json

import pytest
from typer.testing import CliRunner

from aging_clock_conformance.cli import app
from aging_clock_conformance.serialization import canonical_json

RUNNER = CliRunner()


@pytest.mark.parametrize(
    "arguments",
    [
        ["version"],
        ["list"],
        ["show", "horvath-2013"],
        ["provenance", "horvath-2013"],
        ["registry", "validate"],
        ["conformance", "list"],
        ["conformance", "run", "horvath-2013"],
        ["compare", "--clock", "horvath-2013"],
    ],
)
def test_cli_success_json(arguments):
    result = RUNNER.invoke(app, [*arguments, "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)
    assert not result.stderr


@pytest.mark.parametrize("command", ["validate", "applicability", "score", "coverage"])
def test_missing_metadata_cli_semantics(tmp_path, command):
    path = tmp_path / "sample.csv"
    path.write_text("feature_id,value\ncg00000000,.5\n")
    result = RUNNER.invoke(app, [command, str(path), "--clock", "horvath-2013", "--json"])
    assert result.exit_code == (0 if command == "coverage" else 1), result.output
    report = json.loads(result.stdout)
    assert report["result"] is None
    assert not report["input_validation"]["applicability"]["can_compute"]


def test_unknown_clock_json_error():
    result = RUNNER.invoke(app, ["show", "unavailable", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "ACC_UNKNOWN_CLOCK"


def test_invalid_input_json_error(tmp_path):
    result = RUNNER.invoke(
        app, ["validate", str(tmp_path / "missing.csv"), "--clock", "horvath-2013", "--json"]
    )
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "ACC_INPUT_UNREADABLE"


def test_polished_conformance_output():
    result = RUNNER.invoke(app, ["conformance", "run", "horvath-2013"])
    assert result.exit_code == 0
    assert "passed: 16; failed: 0" in result.stdout
    assert "normalized beta" in result.stdout
    assert "recorded" in result.stdout


def test_quiet_preserves_json_and_exit_codes():
    assert RUNNER.invoke(app, ["--quiet", "list"]).stdout == ""
    assert json.loads(RUNNER.invoke(app, ["--quiet", "list", "--json"]).stdout)


def test_verbose_and_markdown(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("feature_id,value\ncg00000000,.5\n")
    args = ["validate", str(path), "--clock", "horvath-2013"]
    verbose = RUNNER.invoke(app, ["--verbose", *args])
    assert "ACC_GENOME_BUILD_UNKNOWN" in verbose.stdout
    markdown = RUNNER.invoke(app, [*args, "--markdown"])
    assert markdown.exit_code == 1 and "# Horvath" in markdown.stdout


def test_cli_fixture_score(tmp_path, clock, fixture, sample):
    path = tmp_path / "public.csv"
    path.write_bytes(clock.artifact_bytes(fixture.suite.input))
    manifest = tmp_path / "public.json"
    manifest.write_text(
        canonical_json(sample.manifest.model_copy(update={"measurements": "public.csv"}))
    )
    result = RUNNER.invoke(
        app, ["score", str(path), "--clock", "horvath-2013", "--manifest", str(manifest), "--json"]
    )
    assert result.exit_code == 0, result.stdout
    document = json.loads(result.stdout)
    assert document["conformance"]["passed"] == 16
    assert document["result"]["value"] == pytest.approx(60.2774909978736, abs=1e-10)


def test_cli_rejects_unselected_matrix(tmp_path):
    path = tmp_path / "matrix.csv"
    path.write_text("feature_id,a,b\ncg00000000,.1,.2\n")
    result = RUNNER.invoke(
        app, ["score", str(path), "--clock", "horvath-2013", "--format", "matrix", "--json"]
    )
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "ACC_SAMPLE_SELECTION_REQUIRED"


def test_cli_comparison_failure_is_nonzero(monkeypatch):
    from aging_clock_conformance import comparison_report
    from aging_clock_conformance.registry import Registry

    good = comparison_report(Registry.load_default().get("horvath-2013"))
    bad = good.model_copy(
        update={"comparison": good.comparison.model_copy(update={"passed": False})}
    )
    monkeypatch.setattr("aging_clock_conformance.cli.comparison_report", lambda *args: bad)
    result = RUNNER.invoke(app, ["compare", "--clock", "horvath-2013", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["comparison"]["passed"] is False
