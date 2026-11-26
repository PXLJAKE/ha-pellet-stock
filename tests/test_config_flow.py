"""Tests for the setup assistant."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pellet_stock.const import DOMAIN


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """A name is enough to create a storage entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "  Pelletsilo  "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Pelletsilo"
    assert result["data"] == {"name": "Pelletsilo"}


async def test_duplicate_name_aborts(hass: HomeAssistant, mock_entry) -> None:
    """Two storages with the same name are not allowed."""
    mock_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Pelletsilo"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_multiple_storages_allowed(hass: HomeAssistant, mock_entry) -> None:
    """A second storage with another name can be added."""
    mock_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Sacklager"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
