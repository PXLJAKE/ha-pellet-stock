"""Build the documentation site and pack it for manual upload.

The site is built with a placeholder domain. The domain is then removed from
every text file, so all links start with /docs/ha-pellet-stock/ and work on
any domain. The result is dist/ha-pellet-stock-docs-<version>.zip with exactly
one folder ha-pellet-stock/ inside.

Usage: python scripts/build_docs.py [version]
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "ha-pellet-stock"
PLACEHOLDER = "https://example.invalid"
SITE = ROOT / "site" / PROJECT
TEXT_SUFFIXES = {".html", ".xml", ".json", ".js", ".css", ".txt"}


def main() -> int:
    """Build, strip the placeholder domain and write the ZIP."""
    manifest = ROOT / "custom_components" / "pellet_stock" / "manifest.json"
    version = (
        sys.argv[1]
        if len(sys.argv) > 1
        else json.loads(manifest.read_text())["version"]
    )

    shutil.rmtree(ROOT / "site", ignore_errors=True)
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict"], cwd=ROOT, check=True
    )

    for path in SITE.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8")
            if PLACEHOLDER in text:
                path.write_text(text.replace(PLACEHOLDER, ""), encoding="utf-8")
    # The compressed sitemap would still hold the placeholder: write it again.
    sitemap = SITE / "sitemap.xml"
    if sitemap.exists():
        (SITE / "sitemap.xml.gz").write_bytes(
            gzip.compress(sitemap.read_bytes(), mtime=0)
        )

    leftovers = [
        str(p.relative_to(SITE))
        for p in SITE.rglob("*")
        if p.is_file() and b"example.invalid" in p.read_bytes()
    ]
    if leftovers:
        print(f"Placeholder domain still in: {leftovers}", file=sys.stderr)
        return 1

    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    target = dist / f"{PROJECT}-docs-{version}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(SITE.rglob("*")):
            if path.is_file():
                archive.write(path, Path(PROJECT) / path.relative_to(SITE))
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
