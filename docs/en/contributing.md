# Contributing

Issues and pull requests are welcome.

- **Problems and ideas:** open an [issue on GitHub](https://github.com/PXLJAKE/ha-pellet-stock/issues).
- **Code:** every change is a pull request, never a direct push to `main`. The checks (lint, tests, hassfest, HACS validation) must pass. The details are in [CONTRIBUTING.md](https://github.com/PXLJAKE/ha-pellet-stock/blob/main/CONTRIBUTING.md).
- **Source code:** [PXLJAKE/ha-pellet-stock](https://github.com/PXLJAKE/ha-pellet-stock), under the [Apache License 2.0](https://github.com/PXLJAKE/ha-pellet-stock/blob/main/LICENSE).

## Build this documentation

```bash
pip install --require-hashes -r requirements_docs.txt
python scripts/build_docs.py
```

The result is `dist/ha-pellet-stock-docs-<version>.zip`. It holds one folder `ha-pellet-stock/` that is copied into the `docs` folder of a website.
