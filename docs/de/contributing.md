# Mitmachen

Issues und Pull Requests sind willkommen.

- **Probleme und Ideen:** Eröffne ein [Issue auf GitHub](https://github.com/PXLJAKE/ha-pellet-stock/issues).
- **Code:** Jede Änderung ist ein Pull Request, nie ein direkter Push auf `main`. Die Prüfungen (Lint, Tests, hassfest, HACS-Validierung) müssen grün sein. Die Einzelheiten stehen in [CONTRIBUTING.md](https://github.com/PXLJAKE/ha-pellet-stock/blob/main/CONTRIBUTING.md) (Englisch).
- **Quellcode:** [PXLJAKE/ha-pellet-stock](https://github.com/PXLJAKE/ha-pellet-stock), unter der [Apache License 2.0](https://github.com/PXLJAKE/ha-pellet-stock/blob/main/LICENSE).

## Diese Dokumentation bauen

```bash
pip install --require-hashes -r requirements_docs.txt
python scripts/build_docs.py
```

Das Ergebnis ist `dist/ha-pellet-stock-docs-<version>.zip`. Darin liegt ein Ordner `ha-pellet-stock/`, der in den `docs`-Ordner einer Website kopiert wird.
