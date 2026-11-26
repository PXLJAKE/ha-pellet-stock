"""Pellet Stock Manager.

Tracks pellet stock, consumption, range and cost for any pellet heating,
independent of the boiler manufacturer.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_IMPORT_HISTORY, DOMAIN
from .frontend import async_register_card
from .manager import PelletStockManager
from .services import async_setup_services
from .websocket import async_register_websocket

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

type PelletStockConfigEntry = ConfigEntry[PelletStockManager]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions (once, for all storages)."""
    async_setup_services(hass)
    async_register_websocket(hass)
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PelletStockConfigEntry) -> bool:
    """Set up one pellet storage from a config entry."""
    manager = PelletStockManager(hass, entry)
    await manager.async_load()
    entry.runtime_data = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    manager.async_start()
    model = manager.model
    if model.history_redo or (
        entry.data.get(CONF_IMPORT_HISTORY) and not model.history_checked
    ):
        # Once, right after setup: fill the charts from the HA statistics.
        # Also once more after data of version 0.2.0 was repaired.
        model.history_checked = True
        model.history_redo = False
        entry.async_create_background_task(
            hass, manager.async_import_history(), f"{DOMAIN}_import_history"
        )
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: PelletStockConfigEntry
) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded


async def async_remove_entry(
    hass: HomeAssistant, entry: PelletStockConfigEntry
) -> None:
    """Delete stored data when the storage is removed."""
    manager = PelletStockManager(hass, entry)
    await manager.async_remove_store()


async def _async_options_updated(
    hass: HomeAssistant, entry: PelletStockConfigEntry
) -> None:
    """Reload when the settings change."""
    await hass.config_entries.async_reload(entry.entry_id)
