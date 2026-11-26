"""Tests for the WebSocket API used by the card."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr


async def test_ws_data(hass: HomeAssistant, mock_entry, hass_ws_client) -> None:
    """The card gets KPIs, months, weeks and the days of a month."""
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    (device,) = dr.async_entries_for_config_entry(
        dr.async_get(hass), mock_entry.entry_id
    )
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "pellet_stock/data", "device_id": device.id, "month": "2026-11"}
    )
    msg = await client.receive_json()
    assert msg["success"]
    data = msg["result"]
    assert data["entry_id"] == mock_entry.entry_id
    assert data["kpis"]["stock_kg"] == 5000
    assert len(data["weeks"]) == 26
    assert len(data["weeks"][0]["days"]) == 7
    assert data["days"] == []

    await client.send_json_auto_id(
        {"type": "pellet_stock/data", "entry_id": mock_entry.entry_id}
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert "days" not in msg["result"]

    await client.send_json_auto_id({"type": "pellet_stock/data", "entry_id": "nope"})
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"
