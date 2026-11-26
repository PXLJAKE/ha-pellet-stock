"""Plain-language explanations ("Why?") for automatic decisions.

State attributes are not translated by Home Assistant, so the texts are
chosen from the system language here (German or English).
"""

from __future__ import annotations

from .model import RangeEstimate

_TEXTS: dict[str, dict[str, str]] = {
    "de": {
        "range_full_days": (
            "Ø {avg:.1f} kg pro Tag aus den letzten {days:.0f} vollen Tagen. "
            "{stock:.0f} kg reichen damit etwa {range:.0f} Tage."
        ),
        "range_partial_day": (
            "Erst {hours:.0f} Stunden Daten: heutiger Verbrauch auf einen Tag "
            "hochgerechnet (Ø {avg:.1f} kg/Tag). Ab morgen wird es genauer."
        ),
        "range_no_data": (
            "Noch zu wenig Daten. Die Reichweite erscheint nach etwa 6 Stunden "
            "mit Verbrauch."
        ),
        "range_no_consumption": (
            "In den letzten {days:.0f} Tagen wurde nichts verbraucht, deshalb "
            "gibt es keine Reichweite."
        ),
        "range_empty": "Das Lager ist leer.",
        "low_stock_yes": (
            "Bestand {stock:.0f} kg liegt unter dem Mindestbestand von "
            "{min:.0f} kg ({percent:.0f} % von {capacity:.0f} kg)."
        ),
        "low_stock_no": (
            "Bestand {stock:.0f} kg liegt über dem Mindestbestand von {min:.0f} kg."
        ),
        "source_baseline": "Startwert {value:.2f} vom Sensor übernommen, noch nichts gezählt.",
        "source_counted": "{kg:.2f} kg Verbrauch gezählt (Sensor stieg auf {value:.2f}).",
        "source_unchanged": "Sensorwert unverändert, nichts gezählt.",
        "source_implausible_jump": (
            "Sprung um {jump:.2f} kg ignoriert, weil er über der Grenze von "
            "{max:.1f} kg pro Schritt liegt (z. B. Neustart oder Messfehler)."
        ),
        "source_reset": "Zähler wurde zurückgesetzt (z. B. Tageswechsel), nichts gezählt.",
        "source_reset_counted": (
            "Zähler wurde zurückgesetzt, {kg:.2f} kg seit dem Zurücksetzen gezählt."
        ),
        "source_small_backstep": (
            "Kleiner Rücksprung des Sensors ignoriert, damit nichts doppelt "
            "gezählt wird."
        ),
        "source_burner_on": "Brenner läuft, Verbrauch wird beim Ausschalten gezählt.",
        "source_burner_off": "Brenner lief {hours:.2f} h, {kg:.2f} kg gezählt.",
        "source_unavailable": "Sensor nicht verfügbar, nichts gezählt.",
        "source_burner_restart": (
            "Home Assistant wurde neu gestartet, während der Brenner lief. Die "
            "Zeit, in der Home Assistant aus war, wird nicht gezählt."
        ),
        "history_imported": (
            "{days:.0f} Tage ({kg:.0f} kg) aus der Home-Assistant-Statistik "
            "übernommen. Die Kosten dieser Tage sind mit dem Durchschnittspreis "
            "von {price:.2f} pro Tonne gerechnet, weil alte Preise nicht bekannt "
            "sind. Der Bestand wurde nicht verändert."
        ),
        "history_no_statistics": (
            "Für den Sensor gibt es keine Langzeitstatistik in Home Assistant, "
            "deshalb wurde kein Verlauf übernommen."
        ),
        "history_not_sensor": (
            "Ein Ein/Aus-Brennerzustand hat keine Langzeitstatistik, deshalb "
            "wurde kein Verlauf übernommen."
        ),
    },
    "en": {
        "range_full_days": (
            "Avg {avg:.1f} kg per day over the last {days:.0f} full days. "
            "{stock:.0f} kg last about {range:.0f} days."
        ),
        "range_partial_day": (
            "Only {hours:.0f} hours of data: today's use extrapolated to a full "
            "day (avg {avg:.1f} kg/day). More accurate from tomorrow."
        ),
        "range_no_data": (
            "Not enough data yet. The range appears after about 6 hours of use."
        ),
        "range_no_consumption": (
            "Nothing was used in the last {days:.0f} days, so there is no range."
        ),
        "range_empty": "The storage is empty.",
        "low_stock_yes": (
            "Stock {stock:.0f} kg is below the minimum of {min:.0f} kg "
            "({percent:.0f} % of {capacity:.0f} kg)."
        ),
        "low_stock_no": "Stock {stock:.0f} kg is above the minimum of {min:.0f} kg.",
        "source_baseline": "Took {value:.2f} from the sensor as starting point, nothing counted yet.",
        "source_counted": "Counted {kg:.2f} kg (sensor rose to {value:.2f}).",
        "source_unchanged": "Sensor value unchanged, nothing counted.",
        "source_implausible_jump": (
            "Ignored a jump of {jump:.2f} kg because it is above the limit of "
            "{max:.1f} kg per step (e.g. restart or measuring error)."
        ),
        "source_reset": "Counter was reset (e.g. new day), nothing counted.",
        "source_reset_counted": "Counter was reset, counted {kg:.2f} kg since the reset.",
        "source_small_backstep": (
            "Ignored a small step back of the sensor so nothing is counted twice."
        ),
        "source_burner_on": "Burner is running, use is counted when it stops.",
        "source_burner_off": "Burner ran {hours:.2f} h, counted {kg:.2f} kg.",
        "source_unavailable": "Sensor unavailable, nothing counted.",
        "source_burner_restart": (
            "Home Assistant restarted while the burner was running. The time "
            "Home Assistant was off is not counted."
        ),
        "history_imported": (
            "Took over {days:.0f} days ({kg:.0f} kg) from the Home Assistant "
            "statistics. Their cost uses the average price of {price:.2f} per "
            "tonne, because older prices are not known. The stock was not changed."
        ),
        "history_no_statistics": (
            "There are no long-term statistics for the sensor in Home Assistant, "
            "so no history was taken over."
        ),
        "history_not_sensor": (
            "An on/off burner state has no long-term statistics, so no history "
            "was taken over."
        ),
    },
}


def language(hass_language: str | None) -> str:
    """Return 'de' for German systems, otherwise 'en'."""
    return "de" if (hass_language or "").lower().startswith("de") else "en"


def text(lang: str, key: str, **values: float) -> str:
    """Return a formatted explanation."""
    return _TEXTS[lang][key].format(**values)


def range_reason(lang: str, est: RangeEstimate, stock_kg: float) -> str:
    """Explain how the range was calculated."""
    match est.basis:
        case "full_days":
            return text(
                lang,
                "range_full_days",
                avg=est.avg_kg_per_day or 0.0,
                days=est.basis_days,
                stock=stock_kg,
                range=est.days or 0.0,
            )
        case "partial_day":
            return text(
                lang,
                "range_partial_day",
                hours=est.basis_days * 24,
                avg=est.avg_kg_per_day or 0.0,
            )
        case "no_consumption":
            return text(lang, "range_no_consumption", days=max(est.basis_days, 1))
        case "empty":
            return text(lang, "range_empty")
        case _:
            return text(lang, "range_no_data")
