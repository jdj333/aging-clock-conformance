"""Explicit CSV contracts that preserve duplicates and do not infer scientific metadata."""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from .errors import ACCError
from .models import Finding, Measurement, Sample, SampleManifest, Severity
from .serialization import canonical_json, parse_document, sha256_bytes

InputFormat = Literal["long", "matrix"]


def load_manifest(path: str | Path) -> SampleManifest:
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ACCError("ACC_INPUT_UNREADABLE", "Sample manifest cannot be read.") from error
    return parse_manifest(raw, yaml_format=path.suffix.lower() in {".yaml", ".yml"})


def parse_manifest(raw: bytes, *, yaml_format: bool = False) -> SampleManifest:
    try:
        return SampleManifest.model_validate(parse_document(raw, yaml_format=yaml_format))
    except ValidationError as error:
        raise ACCError(
            "ACC_INVALID_MANIFEST", "Sample manifest failed schema validation."
        ) from error


def _select(ids: tuple[str, ...], requested: str | None) -> str:
    if not ids:
        raise ACCError("ACC_EMPTY_INPUT", "No sample measurements are present.")
    if any(not identifier for identifier in ids):
        raise ACCError("ACC_SAMPLE_ID_MISSING", "A sample identifier is empty.")
    if requested is not None:
        if requested not in ids:
            raise ACCError("ACC_UNKNOWN_SAMPLE", "Requested sample is not present in the input.")
        return requested
    if len(ids) != 1:
        raise ACCError(
            "ACC_SAMPLE_SELECTION_REQUIRED", "Select one sample explicitly for multi-sample input."
        )
    return ids[0]


def sample_from_bytes(
    raw: bytes,
    *,
    manifest: SampleManifest | None = None,
    sample_id: str | None = None,
    input_format: InputFormat = "long",
    manifest_sha256: str | None = None,
) -> Sample:
    if manifest and sample_id and sample_id != manifest.sample_id:
        raise ACCError("ACC_SAMPLE_MISMATCH", "Manifest and selected sample identifiers differ.")
    requested = sample_id or (manifest.sample_id if manifest else None)
    try:
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
    except (csv.Error, UnicodeError) as error:
        raise ACCError("ACC_MALFORMED_CSV", "Input is not well-formed UTF-8 CSV.") from error
    if len(rows) < 2:
        raise ACCError("ACC_EMPTY_INPUT", "CSV needs a header and measurements.")
    header, body = rows[0], rows[1:]
    if len(header) != len(set(header)) or any(not c for c in header):
        raise ACCError("ACC_DUPLICATE_HEADER", "CSV headers must be nonempty and unique.")
    if any(len(row) != len(header) for row in body):
        raise ACCError("ACC_ROW_WIDTH", "Every CSV row must match the declared header width.")
    measurements: list[Measurement] = []
    if input_format == "long":
        required = {"feature_id", "value"}
        permitted = required | {"sample_id", "unit", "source_column", "quality_flag"}
        if not required.issubset(header) or set(header) - permitted:
            raise ACCError(
                "ACC_CSV_COLUMNS",
                "Long CSV requires feature_id,value and documented optional columns.",
            )
        records = [dict(zip(header, row, strict=True)) for row in body]
        if "sample_id" in header:
            selected = _select(tuple(sorted({r["sample_id"] for r in records})), requested)
            records = [r for r in records if r["sample_id"] == selected]
        else:
            selected = requested or "unidentified-sample"
        measurements = [
            Measurement(
                feature_id=r["feature_id"],
                value=r["value"],
                unit=r.get("unit") or None,
                source_column=r.get("source_column") or None,
                quality_flag=r.get("quality_flag") or None,
            )
            for r in records
        ]
    elif input_format == "matrix":
        if len(header) < 2 or header[0] not in {"feature_id", "probe_id"}:
            raise ACCError(
                "ACC_CSV_COLUMNS", "Matrix CSV needs feature_id/probe_id then sample columns."
            )
        selected = _select(tuple(header[1:]), requested)
        column = header.index(selected)
        measurements = [
            Measurement(feature_id=r[0], value=r[column], source_column=selected) for r in body
        ]
    else:
        raise ACCError("ACC_INPUT_FORMAT", "Unsupported input format.")
    digest = sha256_bytes(raw)
    findings: list[Finding] = []
    if not requested and selected == "unidentified-sample":
        findings.append(
            Finding(
                code="ACC_SAMPLE_ID_UNDECLARED",
                severity=Severity.WARNING,
                category="metadata",
                message="A placeholder labels this unnamed sample; "
                "no biological metadata was inferred.",
            )
        )
    if manifest and manifest.measurements_sha256 and manifest.measurements_sha256 != digest:
        findings.append(
            Finding(
                code="ACC_INPUT_CHECKSUM_MISMATCH",
                severity=Severity.BLOCKING,
                category="schema",
                message="Input bytes do not match the manifest checksum.",
            )
        )
    return Sample(
        sample_id=selected,
        measurements=tuple(measurements),
        manifest=manifest,
        input_sha256=digest,
        manifest_sha256=manifest_sha256 or manifest_digest(manifest),
        input_findings=tuple(findings),
    )


def manifest_digest(manifest: SampleManifest | None) -> str | None:
    return sha256_bytes(canonical_json(manifest).encode()) if manifest else None


def load_sample(
    path: str | Path,
    *,
    manifest: str | Path | SampleManifest | None = None,
    sample_id: str | None = None,
    input_format: InputFormat | None = None,
) -> Sample:
    path = Path(path)
    metadata = manifest if isinstance(manifest, SampleManifest) else None
    digest = None
    if isinstance(manifest, str | Path):
        manifest_path = Path(manifest)
        try:
            raw_manifest = manifest_path.read_bytes()
        except OSError as error:
            raise ACCError("ACC_INPUT_UNREADABLE", "Sample manifest cannot be read.") from error
        metadata = parse_manifest(
            raw_manifest, yaml_format=manifest_path.suffix.lower() in {".yaml", ".yml"}
        )
        digest = sha256_bytes(raw_manifest)
        if (
            metadata.measurements
            and (manifest_path.parent / metadata.measurements).resolve() != path.resolve()
        ):
            raise ACCError(
                "ACC_MANIFEST_INPUT_MISMATCH", "Manifest names a different measurement file."
            )
    if input_format and metadata and input_format != metadata.input_format:
        raise ACCError("ACC_INPUT_FORMAT", "Explicit format conflicts with the manifest.")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ACCError("ACC_INPUT_UNREADABLE", "Sample measurement file cannot be read.") from error
    return sample_from_bytes(
        raw,
        manifest=metadata,
        sample_id=sample_id,
        input_format=input_format or (metadata.input_format if metadata else "long"),
        manifest_sha256=digest,
    )


def inline_sample(
    measurements: tuple[Measurement, ...],
    manifest: SampleManifest | None = None,
    *,
    sample_id: str | None = None,
) -> Sample:
    """Hash an explicit in-memory sample. Never dereference manifest paths or URLs."""
    if manifest and manifest.measurements is not None:
        raise ACCError(
            "ACC_INLINE_PATH_FORBIDDEN", "Inline input cannot reference a local measurement file."
        )
    if sample_id and manifest and sample_id != manifest.sample_id:
        raise ACCError("ACC_SAMPLE_MISMATCH", "Manifest and sample identifiers differ.")
    # Encode special numeric values as their literal tokens for a valid JSON checksum;
    # retain the original values for the validator to reject, never zero/null coercion.
    serialized = []
    for row in measurements:
        record = row.model_dump()
        if isinstance(row.value, float) and not math.isfinite(row.value):
            record["value"] = repr(row.value)
        serialized.append(record)
    digest = sha256_bytes(canonical_json(serialized).encode())
    findings: tuple[Finding, ...] = ()
    if manifest and manifest.measurements_sha256 and manifest.measurements_sha256 != digest:
        findings = (
            Finding(
                code="ACC_INPUT_CHECKSUM_MISMATCH",
                severity=Severity.BLOCKING,
                category="schema",
                message="Inline data differs from the declared canonical checksum.",
            ),
        )
    return Sample(
        sample_id=sample_id or (manifest.sample_id if manifest else "unidentified-sample"),
        measurements=measurements,
        manifest=manifest,
        input_sha256=digest,
        manifest_sha256=manifest_digest(manifest),
        input_findings=findings,
    )
