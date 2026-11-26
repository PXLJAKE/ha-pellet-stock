"""Tests for serving the dashboard card."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


class _Urls(set):
    """Stand-in for the frontend's URL manager."""


async def test_card_is_served_and_registered(
    hass: HomeAssistant, hass_client, mock_entry
) -> None:
    """The card file is served and added to the frontend modules."""
    hass.data["frontend_extra_module_url"] = urls = _Urls()
    assert await async_setup_component(hass, "http", {})
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    assert any(
        u.startswith("/pellet_stock_static/pellet-stock-card.js?v=") for u in urls
    )
    client = await hass_client()
    resp = await client.get("/pellet_stock_static/pellet-stock-card.js")
    assert resp.status == 200
    assert "customElements.define" in await resp.text()
