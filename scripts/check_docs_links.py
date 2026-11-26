"""Check the built documentation the way it is hosted.

Unpacks the ZIP into a folder docs/, serves it with a plain HTTP server and
fetches every internal link, asset and sitemap entry. All of them must start
with /docs/ha-pellet-stock/ and answer with 200.

Usage: python scripts/check_docs_links.py   (after scripts/build_docs.py)
"""

from __future__ import annotations

import functools
import http.server
from pathlib import Path
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
START = "/docs/ha-pellet-stock/"
EXTERNAL = ("http:", "https:", "mailto:", "data:", "javascript:")
LINK = re.compile(r'(?:href|src)="([^"]+)"|<loc>([^<]+)</loc>')


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Static file handler that does not log every request."""

    def log_message(self, format: str, *args: object) -> None:
        """Stay quiet."""


def main() -> int:
    """Serve the newest ZIP and crawl it."""
    archives = sorted((ROOT / "dist").glob("ha-pellet-stock-docs-*.zip"))
    if not archives:
        print("No ZIP in dist/. Run scripts/build_docs.py first.", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(archives[-1]) as archive:
            top = {name.split("/")[0] for name in archive.namelist()}
            if top != {"ha-pellet-stock"}:
                print(f"ZIP must hold exactly one folder, found {top}", file=sys.stderr)
                return 1
            archive.extractall(Path(tmp) / "docs")
        handler = functools.partial(_QuietHandler, directory=tmp)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            pages, bad = _crawl(base)
        finally:
            server.shutdown()
    for problem in bad:
        print(problem, file=sys.stderr)
    print(f"{pages} URLs checked, {len(bad)} problems")
    return 1 if bad else 0


def _crawl(base: str) -> tuple[int, list[str]]:
    seen: set[str] = set()
    todo = [START, START + "sitemap.xml", START + "404.html"]
    bad: list[str] = []
    while todo:
        url = todo.pop()
        if url in seen:
            continue
        seen.add(url)
        try:
            with urllib.request.urlopen(base + urllib.parse.quote(url)) as response:
                body = response.read()
                kind = response.headers.get("content-type", "")
        except urllib.error.HTTPError as err:
            bad.append(f"{err.code} {url}")
            continue
        if "html" not in kind and not url.endswith(".xml"):
            continue
        for match in LINK.finditer(body.decode("utf-8", "replace")):
            link = (match[1] or match[2]).split("#")[0].split("?")[0]
            if not link or link.startswith(EXTERNAL):
                continue
            target = urllib.parse.urljoin(url, link)
            if target.startswith(START):
                todo.append(target)
            else:
                bad.append(f"outside {START}: {link} on {url}")
    return len(seen), bad


if __name__ == "__main__":
    sys.exit(main())
