"""Strict JSON and YAML parsing, deterministic serialization, and digest helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from .errors import ACCError


def canonical_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ACCError("ACC_DUPLICATE_KEY", "Duplicate object key in structured input.")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ACCError("ACC_NONFINITE_JSON", "JSON numeric constants must be finite.")


class UniqueSafeLoader(yaml.SafeLoader):
    pass


def _yaml_mapping(loader: UniqueSafeLoader, node: yaml.MappingNode) -> dict[str, Any]:
    if not isinstance(node, yaml.MappingNode):
        raise ACCError("ACC_INVALID_MANIFEST", "Manifest must contain a mapping.")
    pairs = []
    for key, value in node.value:
        parsed_key = loader.construct_object(key, deep=True)
        if not isinstance(parsed_key, str):
            raise ACCError("ACC_INVALID_MANIFEST", "Manifest keys must be strings.")
        pairs.append((parsed_key, loader.construct_object(value, deep=True)))
    return _pairs(pairs)


UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_mapping)


def parse_document(data: bytes, *, yaml_format: bool = False) -> Any:
    try:
        text = data.decode("utf-8-sig")
        if yaml_format:
            return yaml.load(text, Loader=UniqueSafeLoader)
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError, yaml.YAMLError) as error:
        raise ACCError("ACC_INVALID_DOCUMENT", "Input is not valid UTF-8 JSON/YAML.") from error


def safe_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if Path(relative).is_absolute() or not candidate.is_relative_to(root.resolve()):
        raise ACCError("ACC_UNSAFE_PATH", "Artifact path must stay inside the registry root.")
    return candidate
