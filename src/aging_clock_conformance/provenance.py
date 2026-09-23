"""Local execution evidence, with no user identity, hostname, or absolute sample paths."""

from __future__ import annotations

import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .conformance.fixtures import load_fixture
from .models import Provenance, Sample
from .registry import Clock

PROJECT_VERSION = "0.1.0"


def git_state() -> tuple[str | None, bool | None]:
    root = Path(__file__).resolve().parents[2]
    if not (root / ".git").exists() or not (root / "pyproject.toml").exists():
        return None, None
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    return (
        commit.stdout.strip() if commit.returncode == 0 else None,
        bool(status.stdout.strip()) if status.returncode == 0 else None,
    )


def get_provenance(clock: Clock, sample: Sample | None = None) -> Provenance:
    fixture = load_fixture(clock)
    artifacts = (
        clock.definition.coefficients,
        clock.definition.fixture_manifest,
        fixture.suite.input,
        fixture.suite.expected,
        *fixture.suite.supporting_artifacts,
    )
    checksums = {artifact.path: artifact.sha256 for artifact in artifacts}
    versions = {}
    for package in ("aging-clock-conformance", "pydantic", "typer", "PyYAML", "mcp"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            continue
    commit, dirty = git_state()
    return Provenance(
        project_version=PROJECT_VERSION,
        git_commit=commit,
        git_dirty=dirty,
        clock_version=clock.definition.version,
        clock_definition_sha256=clock.definition_sha256,
        input_sha256=sample.input_sha256 if sample else None,
        manifest_sha256=sample.manifest_sha256 if sample else None,
        reference_checksums=checksums,
        execution_timestamp=datetime.now(UTC).isoformat(),
        python_version=platform.python_version(),
        package_versions=versions,
        operating_system=f"{platform.system()} {platform.release()} {platform.machine()}",
        sources=clock.definition.sources,
    )
