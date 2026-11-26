"""Diagnostics support for Pellet Stock Manager."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import PelletStockConfigEntry

# Free text fields may contain personal information (supplier, notes).
TO_REDACT: set[str] = {"note", "supplier"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PelletStockConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    manager = entry.runtime_data
    model = manager.model
    estimate = manager.estimate()
    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "state": {
            "stock_kg": model.stock_kg,
            "avg_price_per_kg": model.avg_price_per_kg,
            "total_consumed_kg": model.total_consumed_kg,
            "tracking_since": model.tracking_since,
            "counter_baseline": model.counter.baseline,
            "runtime_on_since": model.runtime_on_since,
            "days_stored": len(model.daily_kg),
            "deliveries": async_redact_data(
                [
                    {
                        "date": d.date,
                        "kg": d.kg,
                        "price_total": d.price_total,
                        "note": d.note,
                    }
                    for d in model.deliveries
                ],
                TO_REDACT,
            ),
            "low_stock": manager.low_stock,
            "range_basis": estimate.basis,
            "last_decision": manager.last_decision.reason
            if manager.last_decision
            else None,
        },
    }
