# Contributing

Every change goes through a pull request; nothing is pushed to `main` directly.

## Local checks

```bash
python3.14 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
ruff check . && ruff format --check .
python -m pytest --cov
```

## Guidelines

- Async only, no blocking I/O in the event loop, no polling where an event works.
- Write to disk rarely (Raspberry Pi SD cards): batch saves, no per-update writes.
- No secrets in code or logs. Diagnostics redact free text.
- Every setting and every automatic decision gets a plain-language explanation
  in German and English.

## Releasing

1. In a pull request, raise `version` in `custom_components/pellet_stock/manifest.json` and move the changelog entries from *Unreleased* to a new section `## [x.y.z] - date`.
2. Merge it. The release workflow publishes `vx.y.z` with the changelog section as text and a ZIP for manual installation, and HACS offers the update. A version with a hyphen (`0.3.0-beta.1`) becomes a pre-release. No version change, no release.

## Documentation

The documentation site is in `docs/en` and `docs/de` and is built with MkDocs. Keep both languages in step.

```bash
pip install --require-hashes -r requirements_docs.txt
python scripts/build_docs.py          # builds dist/ha-pellet-stock-docs-<version>.zip
python scripts/check_docs_links.py    # serves it under /docs/ha-pellet-stock/ and checks every link
```

The site is not deployed automatically. The ZIP is attached to every full release and holds one folder `ha-pellet-stock/` that is copied by hand. To change the pinned tools, edit `requirements_docs.in` and run `pip-compile --generate-hashes --strip-extras -o requirements_docs.txt requirements_docs.in`.
