"""Verify reproducible wheel/sdist bytes and installed-wheel conformance outside the checkout."""

import hashlib
import os
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> None:
    environment = {**os.environ, "SOURCE_DATE_EPOCH": "1735689600", "PYTHONHASHSEED": "0"}
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="acc-build-") as temp:
        work = Path(temp)
        for name in ("first", "second"):
            run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--no-isolation",
                    "--outdir",
                    str(work / name),
                    str(ROOT),
                ],
                cwd=work,
                env=environment,
            )
        first = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (work / "first").iterdir()
        }
        second = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (work / "second").iterdir()
        }
        if first != second or len(first) != 2:
            raise SystemExit("Wheel/source builds differ.")
        # Test wheel rebuilt from the sdist by `build`, independent of source imports.
        wheel = next((work / "first").glob("*.whl"))
        archive = next((work / "first").glob("*.tar.gz"))
        with tarfile.open(archive) as handle:
            names = handle.getnames()
            if not any(name.endswith("NOTICE.md") for name in names):
                raise SystemExit("Source archive is missing third-party attribution.")
        venv = work / "installed"
        run([sys.executable, "-m", "venv", str(venv)], cwd=work, env=environment)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        site_packages = Path(
            subprocess.check_output(
                [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
                text=True,
                env=environment,
            ).strip()
        )
        # Reuse locked dependencies offline. Adding this directory does not process
        # its editable-install .pth files; the wheel's own package takes precedence.
        (site_packages / "locked_dependencies.pth").write_text(sysconfig.get_path("purelib") + "\n")
        run(
            [str(python), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)],
            cwd=work,
            env=environment,
        )
        run(
            [
                str(python),
                "-I",
                "-c",
                "from pathlib import Path; import aging_clock_conformance as a; "
                "import sys; assert Path(a.__file__).is_relative_to(Path(sys.prefix)); "
                "c=a.Registry.load_default().get('horvath-2013'); "
                "assert a.run_conformance(c).passed == 16; "
                "assert a.compare_implementations(c).passed; "
                "print('Installed wheel: registry, fixtures, both implementations verified.')",
            ],
            cwd=work,
            env=environment,
        )
        for name, digest in first.items():
            print(f"Reproducible: {name} sha256:{digest}")


if __name__ == "__main__":
    main()
