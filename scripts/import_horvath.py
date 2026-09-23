"""Import only pinned public reference artifacts from an existing upstream checkout.

No download, recursive copy, expectation generation, or automatic hash updates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "src/aging_clock_conformance/data"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan = json.loads((ROOT / "scripts/reference-imports.json").read_text())
    revision = subprocess.check_output(
        ["git", "-C", str(args.upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != plan["revision"]:
        raise SystemExit("Upstream HEAD differs from the pinned reference revision.")
    verified = []
    for item in plan["artifacts"]:
        source = (args.upstream / item["upstream_path"]).resolve()
        destination = (DESTINATION / item["path"]).resolve()
        if not source.is_relative_to(args.upstream.resolve()):
            raise SystemExit("Source escapes checkout.")
        if not destination.is_relative_to(DESTINATION.resolve()):
            raise SystemExit("Destination escapes package data directory.")
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise SystemExit(f"Source digest mismatch: {item['role']}")
        if destination.exists() and destination.read_bytes() != raw:
            raise SystemExit("Existing immutable artifact differs; introduce a new version.")
        verified.append((destination, raw))
    for destination, raw in verified:
        if args.check:
            if not destination.exists() or destination.read_bytes() != raw:
                raise SystemExit("Imported artifact is missing or differs.")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
    print(f"Verified {len(verified)} explicitly selected public artifacts at {revision}.")


if __name__ == "__main__":
    main()
