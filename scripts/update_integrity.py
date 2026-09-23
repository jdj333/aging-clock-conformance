"""Explicitly rebuild package inventory after a reviewed source/specification change.

Does not rewrite fixture source hashes or expected results. Review diffs; changing
the inventory cannot legitimize a changed immutable artifact.
"""

from pathlib import Path

from aging_clock_conformance.serialization import canonical_json, sha256_file

ROOT = Path(__file__).resolve().parents[1] / "src/aging_clock_conformance/data"


def main() -> None:
    files = {
        str(path.relative_to(ROOT)): sha256_file(path)
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and path.name != "integrity.json"
    }
    (ROOT / "integrity.json").write_text(canonical_json({"schema_version": "1.0", "files": files}))
    print(f"Wrote inventory for {len(files)} files; inspect the diff before committing.")


if __name__ == "__main__":
    main()
