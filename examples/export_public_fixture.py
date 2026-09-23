"""Export a public reference sample as long CSV and a checksum-bound manifest."""

import argparse
import csv
import io
from pathlib import Path

from aging_clock_conformance import Registry, load_fixture
from aging_clock_conformance.serialization import canonical_json, sha256_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path, help="New directory; never overwrite."
    )
    parser.add_argument("--sample", default="GSM946048")
    args = parser.parse_args()
    clock = Registry.load_default().get("horvath-2013")
    fixture = load_fixture(clock)
    matches = [case for case in fixture.cases if case.sample.sample_id == args.sample]
    if len(matches) != 1:
        parser.error("Sample is not present in the public reference fixture.")
    sample = matches[0].sample
    assert sample.manifest is not None
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["feature_id", "value"])
    writer.writerows((row.feature_id, row.value) for row in sample.measurements)
    raw = buffer.getvalue().encode()
    metadata = sample.manifest.model_copy(
        update={
            "measurements": "sample.csv",
            "measurements_sha256": sha256_bytes(raw),
            "input_format": "long",
        }
    )
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "sample.csv").write_bytes(raw)
    (args.output / "sample.json").write_text(canonical_json(metadata))
    (args.output / "provenance.json").write_text(
        canonical_json(
            {
                "source_fixture": fixture.suite.fixture_id,
                "version": fixture.suite.version,
                "sample_id": sample.sample_id,
                "source_sha256": fixture.suite.input.sha256,
                "export_sha256": sha256_bytes(raw),
                "license": "CC-BY-2.0",
                "transformation": "Select one public sample column and serialize as long CSV; "
                "no numeric calculation or normalization.",
            }
        )
    )
    print(f"Exported public sample {sample.sample_id} to {args.output}.")


if __name__ == "__main__":
    main()
