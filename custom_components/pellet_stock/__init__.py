"""Pellet Stock Manager.

Tracks pellet stock, consumption, range and cost for any pellet heating,
independent of the boiler manufacturer.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

# Platforms are added step by step in the MVP pull requests.
PLATFORMS: list[Platform] = []


@dataclass(slots=True)
class PelletStockData:
    """Runtime data for one pellet storage."""

    name: str


type PelletStockConfigEntry = ConfigEntry[PelletStockData]


async def async_setup_entry(hass: HomeAssistant, entry: PelletStockConfigEntry) -> bool:
    """Set up one pellet storage from a config entry."""
    entry.runtime_data = PelletStockData(name=entry.title)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: PelletStockConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
