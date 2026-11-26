"""Tests for diagnostics."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pellet_stock.const import DOMAIN
from custom_components.pellet_stock.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_free_text(hass: HomeAssistant) -> None:
    """Notes and supplier names never appear in diagnostics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Pelletsilo",
        data={"name": "Pelletsilo"},
        options={"note": "Herr Müller, Tel. 0123", "supplier": "Pellets Müller"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"] == {"name": "Pelletsilo"}
    assert diag["entry"]["options"] == {
        "note": "**REDACTED**",
        "supplier": "**REDACTED**",
    }
