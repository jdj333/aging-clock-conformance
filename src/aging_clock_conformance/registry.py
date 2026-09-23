"""Load and verify versioned clock assets without network access."""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .errors import ACCError
from .models import Artifact, ClockDefinition
from .serialization import parse_document, safe_path, sha256_bytes


@dataclass(frozen=True)
class Clock:
    definition: ClockDefinition
    root: Path
    definition_sha256: str
    coefficients: tuple[tuple[str, float], ...]

    @property
    def required_features(self) -> tuple[str, ...]:
        return tuple(feature for feature, _ in self.coefficients)

    def artifact_bytes(self, artifact: Artifact) -> bytes:
        return verified_bytes(self.root, artifact.path, artifact.sha256)


def verified_bytes(root: Path, relative: str, expected: str) -> bytes:
    path = safe_path(root, relative)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ACCError(
            "ACC_ARTIFACT_MISSING", f"Required registry artifact unavailable: {relative}"
        ) from error
    if sha256_bytes(raw) != expected:
        raise ACCError("ACC_CHECKSUM_MISMATCH", f"Registry artifact checksum mismatch: {relative}")
    return raw


def load_coefficients(definition: ClockDefinition, raw: bytes) -> tuple[tuple[str, float], ...]:
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)):
            raise ValueError("Duplicate coefficient headers")
        rows = list(reader)
        if len(rows) != definition.feature_contract.count + 1:
            raise ValueError("Wrong coefficient count")
        intercepts = [r for r in rows if r[definition.feature_column] == definition.intercept_label]
        if len(intercepts) != 1:
            raise ValueError("Exactly one intercept is required")
        if float(intercepts[0][definition.coefficient_column]) != definition.intercept:
            raise ValueError("Intercept differs from definition")
        coefficients = tuple(
            (row[definition.feature_column], float(row[definition.coefficient_column]))
            for row in rows
            if row[definition.feature_column] != definition.intercept_label
        )
        identifiers = [feature for feature, _ in coefficients]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Duplicate coefficient features")
        if not all(
            re.fullmatch(definition.feature_contract.identifier_pattern, f) and math.isfinite(c)
            for f, c in coefficients
        ):
            raise ValueError("Invalid coefficient or identifier")
    except (ValueError, KeyError, TypeError, UnicodeError, csv.Error, re.error) as error:
        raise ACCError(
            "ACC_INVALID_COEFFICIENTS", "Coefficient artifact violates its clock contract."
        ) from error
    return coefficients


class Registry:
    """An explicit registry root. Built-in assets ship in both wheel and source archive."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    @classmethod
    def load_default(cls) -> Registry:
        return cls(Path(__file__).parent / "data")

    def verify_integrity(self) -> dict[str, str]:
        try:
            raw = (self.root / "integrity.json").read_bytes()
        except OSError as error:
            raise ACCError(
                "ACC_REGISTRY_INVALID", "Registry integrity manifest is unavailable."
            ) from error
        document = parse_document(raw)
        if not isinstance(document, dict) or document.get("schema_version") != "1.0":
            raise ACCError("ACC_REGISTRY_INVALID", "Invalid registry integrity manifest.")
        entries = document.get("files")
        if not isinstance(entries, dict) or not entries:
            raise ACCError("ACC_REGISTRY_INVALID", "Registry integrity manifest has no files.")
        for path, digest in entries.items():
            if (
                not isinstance(path, str)
                or not isinstance(digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
            ):
                raise ACCError("ACC_REGISTRY_INVALID", "Invalid integrity manifest entry.")
            verified_bytes(self.root, path, digest)
        actual = {
            str(p.relative_to(self.root))
            for p in self.root.rglob("*")
            if p.is_file() and p.name != "integrity.json"
        }
        if actual != set(entries):
            raise ACCError(
                "ACC_REGISTRY_INVALID", "Registry contains unlisted or missing artifacts."
            )
        return entries

    def list(self) -> tuple[Clock, ...]:
        self.verify_integrity()
        clocks = tuple(self._read(path) for path in sorted(self.root.glob("clocks/*/clock.json")))
        if not clocks:
            raise ACCError("ACC_REGISTRY_INVALID", "No clocks are registered.")
        names = [
            name
            for clock in clocks
            for name in (clock.definition.clock_id, *clock.definition.aliases)
        ]
        if len(names) != len(set(names)):
            raise ACCError("ACC_REGISTRY_INVALID", "Clock identifiers and aliases must be unique.")
        return clocks

    def get(self, clock_id: str) -> Clock:
        for clock in self.list():
            if clock_id in (clock.definition.clock_id, *clock.definition.aliases):
                return clock
        raise ACCError("ACC_UNKNOWN_CLOCK", "Clock is not present in this registry.")

    def _read(self, path: Path) -> Clock:
        raw = path.read_bytes()
        try:
            definition = ClockDefinition.model_validate(parse_document(raw))
        except ValidationError as error:
            raise ACCError(
                "ACC_REGISTRY_INVALID", "Clock definition failed schema validation."
            ) from error
        if path.parent.name != definition.clock_id:
            raise ACCError("ACC_REGISTRY_INVALID", "Clock directory and identifier differ.")
        coefficients = load_coefficients(
            definition,
            verified_bytes(self.root, definition.coefficients.path, definition.coefficients.sha256),
        )
        verified_bytes(
            self.root, definition.fixture_manifest.path, definition.fixture_manifest.sha256
        )
        return Clock(definition, self.root, sha256_bytes(raw), coefficients)
