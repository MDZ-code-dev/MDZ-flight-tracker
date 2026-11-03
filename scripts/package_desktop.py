#!/usr/bin/env python3
"""Build Linux and Windows portable source archives from a clean file list."""
import argparse
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        package = Path(tmp) / "MDZ-SkyScan"
        package.mkdir()
        for name in ("app.py", "desktop.py", "README.md"):
            shutil.copy2(ROOT / name, package / name)
        shutil.copytree(ROOT / "web", package / "web")
        launcher = package / "MDZ-SkyScan.sh"
        shutil.copy2(ROOT / "packaging/linux/MDZ-SkyScan.sh", launcher)
        launcher.chmod(0o755)
        with tarfile.open(args.output / "MDZ-SkyScan-linux.tar.gz", "w:gz") as archive:
            archive.add(package, arcname=package.name)
        launcher.unlink()
        shutil.copy2(ROOT / "packaging/windows/MDZ-SkyScan.cmd", package / "MDZ-SkyScan.cmd")
        with zipfile.ZipFile(args.output / "MDZ-SkyScan-windows-portable.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(package.parent))
    print(f"Desktop archives written to {args.output}")


if __name__ == "__main__":
    main()
