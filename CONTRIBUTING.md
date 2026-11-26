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
