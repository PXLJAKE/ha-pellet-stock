# Fehlersuche

## Die Karte fehlt

Die Karte wird beim Start von Home Assistant geladen. Nach dem Installieren oder Aktualisieren:

1. Starte Home Assistant neu.
2. Lade die Browserseite ohne Cache neu (am PC: Strg+Umschalt+R).
3. In der Companion-App: **Einstellungen → Companion-App → Fehlerbehebung → Frontend-Cache zurücksetzen**.

Zeigt ein Dashboard „Custom element doesn't exist: pellet-stock-card“, hat der Browser noch eine alte Seite. Dieselben Schritte helfen.

## Die Reichweite ist unbekannt

Für eine Reichweite braucht es etwa 6 Stunden Verbrauch. Das Attribut `reason` des Sensors *Reichweite* sagt, was fehlt, zum Beispiel „Noch zu wenig Daten“ oder „In den letzten 14 Tagen wurde nichts verbraucht“.

## Der Bestand sinkt nicht

Schau ins Attribut `reason` beim *Gesamtverbrauch*. Es erklärt, was mit dem letzten Sensorwert passiert ist:

- **„Sprung um … ignoriert“**: Der Schritt war größer als der *größte plausible Schritt*. Meldet dein Kessel in großen Schritten, erhöhe den Wert unter **Konfigurieren**.
- **„Sensor nicht verfügbar“**: Der Quellsensor hat gerade keinen Wert.
- **„Sensorwert unverändert“**: Der Kessel hat keinen neuen Verbrauch gemeldet.

## Der Bestand stimmt nicht

Setz ihn mit der Aktion `pellet_stock.correct_stock`, oder mit dem Knopf *Gemessenen Füllstand übernehmen*, wenn du einen Füllstandssensor hast. Verlauf und Lieferungen bleiben erhalten.

## Die Übernahme des Verlaufs bringt nichts

- **„Für den Sensor gibt es keine Langzeitstatistik“**: Home Assistant führt nur für Sensoren mit Zustandsklasse eine Statistik. Prüfe unter **Entwicklerwerkzeuge → Statistik**, ob dein Sensor dort steht.
- **„Der Verlauf wurde schon übernommen“**: Die Übernahme läuft einmal pro Lager, damit nichts doppelt gezählt wird. Zum Neueinlesen führst du die Aktion mit `replace: true` aus.
- Die Aktion `pellet_stock.import_history` fehlt: Du hast eine Version vor 0.2.0. Aktualisiere und starte neu.

## Verbrauch und Kosten sind viel zu hoch

Version 0.2.0 hat den übernommenen Verlauf bei jedem Neustart noch einmal dazugezählt. Aktualisiere auf 0.2.1 oder neuer und starte neu: Der Verlauf wird automatisch entfernt und neu gelesen. Der Bestand war nicht betroffen.

## Eine Lieferung ist falsch

Lösch sie mit `pellet_stock.delete_delivery`. Die `delivery_id` steht in den Attributen des Sensors *Letzte Lieferung*. Trag sie danach neu ein.

## Ein Problem melden

Lade die Diagnose unter **Einstellungen → Geräte & Dienste → Pellet Stock Manager → ⋮ → Diagnose herunterladen** und eröffne ein [Issue auf GitHub](https://github.com/PXLJAKE/ha-pellet-stock/issues). Liefernotizen sind in der Diagnose ausgeblendet.
