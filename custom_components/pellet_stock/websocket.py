"""WebSocket API for the dashboard card: ``pellet_stock/data``.

Returns key figures, months, years, weeks, deliveries and (on request) the
days of one month. The card asks only when it needs the data, so nothing big
lands in the recorder database.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
import voluptuous as vol

from .const import DOMAIN
from .manager import PelletStockManager


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Register the command once."""
    websocket_api.async_register_command(hass, ws_get_data)


def _find_manager(
    hass: HomeAssistant, msg: dict[str, Any]
) -> PelletStockManager | None:
    entry_ids: set[str] = set()
    if entry_id := msg.get("entry_id"):
        entry_ids.add(entry_id)
    device_id = msg.get("device_id")
    if device_id and (device := dr.async_get(hass).async_get(device_id)):
        entry_ids |= set(device.config_entries)
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id in entry_ids and entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/data",
        vol.Optional("entry_id"): str,
        vol.Optional("device_id"): str,
        vol.Optional("month"): vol.Match(r"^\d{4}-\d{2}$"),
    }
)
@callback
def ws_get_data(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send the analysis data of one pellet storage."""
    manager = _find_manager(hass, msg)
    if manager is None:
        connection.send_error(msg["id"], "not_found", "Pellet storage not found")
        return
    connection.send_result(msg["id"], manager.export(msg.get("month")))
