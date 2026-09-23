"""Generate JSON Schema 2020-12 from the public models; --check never writes."""

import argparse
from pathlib import Path

from aging_clock_conformance.models import (
    ClockDefinition,
    FixtureSuite,
    Measurement,
    RunReport,
    SampleManifest,
    ValidationReport,
)
from aging_clock_conformance.serialization import canonical_json

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "clock": ClockDefinition,
    "fixture": FixtureSuite,
    "measurement": Measurement,
    "sample-manifest": SampleManifest,
    "validation-report": ValidationReport,
    "run-report": RunReport,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, model in MODELS.items():
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = (
            f"https://github.com/jdj333/aging-clock-conformance/schemas/{name}.schema.json"
        )
        expected = canonical_json(schema)
        path = ROOT / "schemas" / f"{name}.schema.json"
        if args.check:
            if not path.exists() or path.read_text() != expected:
                raise SystemExit(f"Schema is stale: {path.name}")
        else:
            path.parent.mkdir(exist_ok=True)
            path.write_text(expected)
    print(f"Verified {len(MODELS)} deterministic JSON Schemas.")


if __name__ == "__main__":
    main()
