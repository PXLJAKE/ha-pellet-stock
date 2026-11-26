# Konfiguration

Alles wird in der Oberfläche von Home Assistant eingestellt. Du kannst jede Einstellung später ändern, unter **Einstellungen → Geräte & Dienste → Pellet Stock Manager → Konfigurieren**. Bestand, Lieferungen und Verlauf bleiben dabei erhalten.

## Schritt 1: Name und Quelle

| Feld | Was es tut |
|---|---|
| Name | Wird als Gerätename angezeigt, z. B. „Pelletsilo“. Zwei Lager können nicht gleich heißen. |
| Woher kommt der Verbrauch? | Wähle, was deine Heizung schon in Home Assistant meldet. |

Die drei Quellen:

| Quelle | Wann sie passt |
|---|---|
| Ein Sensor zählt Pellets in kg | Dein Kessel meldet verbrauchte Pellets in kg. Ein Gesamtzähler und ein Tageszähler, der um Mitternacht auf 0 springt, funktionieren beide. |
| Ein Sensor zählt Energie in kWh | Dein Kessel oder ein Wärmemengenzähler zählt Energie. Die Pellets sind die Energie geteilt durch den Heizwert. |
| Brennerlaufzeit | Du weißt nur, wann der Brenner läuft: eine Ein/Aus-Entität oder ein Sensor mit Betriebsstunden. Die Pellets sind die Laufzeit mal kg pro Stunde. |

## Schritt 2: Details zur Quelle

| Feld | Standard | Was es tut |
|---|---|---|
| Sensor | | Die Entität, die gelesen wird. |
| Heizwert | 4,8 kWh/kg | Energie in einem Kilo Pellets. 4,8 kWh/kg ist typisch für ENplus-A1-Pellets, genauer steht es oft auf dem Lieferschein. Wird für den Energie-Sensor und den Preis pro kWh genutzt. |
| Größter plausibler Schritt | 10 kg | Größere Sprünge zwischen zwei Sensorwerten werden ignoriert, z. B. nach einem Neustart oder Messfehler. |
| Kesselwirkungsgrad | 100 % | Nur bei Energie-Sensoren. Lass 100 %, wenn der Sensor die Energie in den Pellets zählt, wie die meisten Kessel. Misst er die abgegebene Wärme, trag den Kesselwirkungsgrad ein, z. B. 90 %. |
| Pellets pro Brennerstunde | 2 kg/h | Nur bei Brennerlaufzeit. Wie viele kg der Brenner pro Stunde bei üblicher Leistung braucht. Steht im Handbuch (Brennstoffverbrauch bei Nennlast) oder lässt sich aus einer Lieferung ausrechnen. |

## Schritt 3: Lager

| Feld | Standard | Was es tut |
|---|---|---|
| Lagergröße | 5000 kg | Wie viele kg ins volle Lager passen. |
| Mindestbestand | 10 % | Unter diesem Anteil der Lagergröße geht der Sensor „Mindestbestand erreicht“ an und das Ereignis `pellet_stock_low_stock` wird ausgelöst. |
| Füllstands- oder Waagensensor | keiner | Optional. Ein Sensor, der misst, was wirklich im Lager ist (Waage, Ultraschall, Radar; in kg oder %). Er wird nur mit dem berechneten Bestand verglichen. Übernommen wird er per Knopf, nie automatisch. |

!!! note "Ein berechneter Füllstand ist keine Messung"
    Manche Kessel melden einen „Lagerstand“, den sie selbst aus dem Verbrauch berechnen. Ein Vergleich mit dem Bestand sagt dann nichts Neues, weil beide aus demselben Zähler kommen. Die Option ist für echte Messungen gedacht.

## Schritt 4: Startwerte

| Feld | Standard | Was es tut |
|---|---|---|
| Aktueller Bestand | | Deine beste Schätzung, was heute im Lager liegt. Mit Füllstandssensor wird dessen Wert vorgeschlagen. Du kannst ihn später korrigieren. |
| Preis pro Tonne | 0 | Was du für diese Pellets bezahlt hast, inklusive Lieferung. Wird für Kosten und Preis pro kWh genutzt. 0 heißt unbekannt. |
| Verlauf aus Home Assistant übernehmen | an | Wird nur angeboten, wenn die Quelle ein Sensor ist. Liest den bisherigen Tagesverbrauch aus der Langzeitstatistik des Sensors, damit die Diagramme ab dem ersten Tag gefüllt sind. Der Bestand wird nicht verändert. |

## So funktioniert die Übernahme des Verlaufs

Home Assistant führt für Sensoren mit Zustandsklasse eine Langzeitstatistik. Sie wird einmal gelesen und in Tagesverbrauch umgerechnet:

- Sensoren mit Gesamtzähler: Die Änderung pro Tag ist der Verbrauch.
- Tageszähler, die um Mitternacht auf 0 springen: Der höchste Wert des Tages ist der Verbrauch.
- Andere Messwerte: höchster minus niedrigster Wert des Tages.

Tage mit mehr als 500 kg gelten als fehlerhaft und werden übersprungen. Es werden bis zu zehn Jahre gelesen. Tageswerte bleiben für die letzten 400 Tage erhalten, ältere Tage zählen nur in den Monats- und Jahressummen. Die Kosten der übernommenen Tage werden mit deinem Durchschnittspreis gerechnet, weil alte Preise nicht bekannt sind.

Die Übernahme läuft einmal pro Lager. Hast du das Lager angelegt, bevor es diese Funktion gab, führe einmal die Aktion `pellet_stock.import_history` aus, siehe [Nutzung](usage.md#aktionen).

Ein Ein/Aus-Brennerzustand hat keine Langzeitstatistik, deshalb gibt es dafür nichts zu übernehmen.
