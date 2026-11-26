# Nutzung

## Entitäten

Jedes Lager ist ein Gerät mit diesen Entitäten:

| Entität | Beschreibung |
|---|---|
| Bestand | Pellets im Lager, in kg |
| Füllgrad | Bestand in Prozent der Lagergröße |
| Reichweite | Tage, die der Bestand reicht. Das Attribut `reason` erklärt die Rechnung |
| Durchschnittlicher Tagesverbrauch | Durchschnitt der letzten 14 vollen Tage |
| Verbrauch heute | Heute verbrauchte kg |
| Gesamtverbrauch | Verbrauchte kg seit der Einrichtung. Das Attribut `reason` erklärt jede automatische Entscheidung |
| Energie | kWh in den verbrauchten Pellets, für das Energie-Dashboard |
| Preis pro kWh | Durchschnittspreis der Pellets geteilt durch den Heizwert |
| Durchschnittspreis pro Tonne | Gleitender Durchschnitt deiner Lieferungen |
| Kosten diesen Monat / Kosten dieses Jahr | Kosten der verbrauchten Pellets |
| Letzte Lieferung | Datum der letzten Lieferung. Die zehn neuesten stehen in den Attributen |
| Mindestbestand erreicht | An, wenn der Bestand unter dem Mindestbestand liegt |
| Abweichung zum Messwert | Nur mit Füllstandssensor: berechneter Bestand minus gemessener Wert |
| Gemessenen Füllstand übernehmen | Nur mit Füllstandssensor: ein Knopf, der den Bestand auf den Messwert setzt |

## Die „Warum?“-Erklärungen

Jede automatische Entscheidung wird in einfacher Sprache erklärt, im Attribut `reason` und auf der Karte.

**Reichweite.** Die Reichweite ist der Bestand geteilt durch den Durchschnittsverbrauch der letzten 14 vollen Tage. In den ersten Stunden wird der heutige Verbrauch auf einen Tag hochgerechnet, und die Erklärung sagt das dazu. Ohne etwa 6 Stunden Verbrauch gibt es noch keine Reichweite.

**Verbrauchssensor.** Die Erklärung beim *Gesamtverbrauch* sagt, was mit dem letzten Sensorwert passiert ist, zum Beispiel:

- „0.42 kg Verbrauch gezählt (Sensor stieg auf 12.30).“
- „Sprung um 25.00 kg ignoriert, weil er über der Grenze von 10.0 kg pro Schritt liegt (z. B. Neustart oder Messfehler).“
- „Zähler wurde zurückgesetzt (z. B. Tageswechsel), nichts gezählt.“
- „Home Assistant wurde neu gestartet, während der Brenner lief. Die Zeit, in der Home Assistant aus war, wird nicht gezählt.“

## Lieferungen

Trag eine Lieferung auf der Karte mit **Lieferung eintragen** ein oder mit der Aktion `pellet_stock.add_delivery`. Der Bestand steigt, und der Durchschnittspreis wird als gleitender Durchschnitt neu berechnet: Wert des Rests plus Wert der Lieferung, geteilt durch den neuen Bestand.

Trägst du Lieferungen auch am Kessel selbst ein, wird nichts doppelt gezählt. Die Integration liest vom Kessel nur den Verbrauch.

## Aktionen

| Aktion | Felder |
|---|---|
| `pellet_stock.add_delivery` | `config_entry_id`, `kg`, `price` (Preis der ganzen Lieferung, optional), `date` (optional, sonst heute), `note` (optional) |
| `pellet_stock.correct_stock` | `config_entry_id`, `stock_kg` (was jetzt wirklich im Lager liegt) |
| `pellet_stock.delete_delivery` | `config_entry_id`, `delivery_id` (aus den Attributen von *Letzte Lieferung*) |
| `pellet_stock.import_history` | `config_entry_id`. Übernimmt den bisherigen Tagesverbrauch aus der Statistik, einmal pro Lager |

Jede Aktion gibt eine Antwort zurück, zum Beispiel den neuen Bestand. Du findest sie unter **Entwicklerwerkzeuge → Aktionen** und wählst dort das Lager aus einer Liste.

## Automation bei Mindestbestand

Das Ereignis `pellet_stock_low_stock` wird einmal ausgelöst, wenn der Bestand unter den Mindestbestand fällt. Es enthält `entry_id`, `name`, `stock_kg`, `min_stock_kg` und `reason`.

```yaml
triggers:
  - trigger: event
    event_type: pellet_stock_low_stock
actions:
  - action: notify.notify
    data:
      title: "Pellets bestellen"
      message: "{{ trigger.event.data.reason }}"
```

Du kannst auch den Binärsensor *Mindestbestand erreicht* als Auslöser nehmen.

## Energie-Dashboard

Der Sensor *Energie* zählt die kWh in den verbrauchten Pellets, und *Preis pro kWh* ist der passende Preis. Du kannst den Sensor *Energie* in den Einstellungen des Energie-Dashboards auswählen.

!!! info "Offener Punkt"
    Welcher Bereich des Energie-Dashboards für Pellets am besten passt, ist noch nicht dokumentiert. Home Assistant hat keine Kategorie für Pellets.
