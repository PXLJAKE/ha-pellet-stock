"""Tests for diagnostics."""

from __future__ import annotations

from datetime import date

from homeassistant.core import HomeAssistant

from custom_components.pellet_stock.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_free_text(hass: HomeAssistant, mock_entry) -> None:
    """Delivery notes never appear in diagnostics."""
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    mock_entry.runtime_data.model.add_delivery(
        1000, 400, date(2026, 11, 1), note="Herr Müller, Tel. 0123"
    )

    diag = await async_get_config_entry_diagnostics(hass, mock_entry)
    assert diag["entry"]["data"]["source_type"] == "kg_counter"
    assert diag["state"]["stock_kg"] == 6000
    assert diag["state"]["deliveries"][0]["note"] == "**REDACTED**"
    assert "Müller" not in str(diag)
