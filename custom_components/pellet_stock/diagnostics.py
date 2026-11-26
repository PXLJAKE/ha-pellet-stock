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
    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
    }
