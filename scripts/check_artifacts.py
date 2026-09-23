"""Validate package integrity, scientific schema contracts, and fixture hashes offline."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from aging_clock_conformance import Registry, load_fixture

ROOT = Path(__file__).resolve().parents[1]


def validate_schema(name: str, instance: object) -> None:
    schema = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def main() -> None:
    registry = Registry.load_default()
    files = registry.verify_integrity()
    for clock in registry.list():
        validate_schema("clock", clock.definition.model_dump(mode="json"))
        fixture = load_fixture(clock)
        validate_schema("fixture", fixture.suite.model_dump(mode="json"))
        for case in fixture.cases:
            validate_schema("sample-manifest", case.sample.manifest.model_dump(mode="json"))
    print(f"Verified schemas, reference structure, and {len(files)} artifact digests.")


if __name__ == "__main__":
    main()
