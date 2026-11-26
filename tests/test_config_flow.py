"""Tests for the setup assistant and the options flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pellet_stock.const import DOMAIN


async def _start(hass: HomeAssistant, name: str, source_type: str):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": name, "source_type": source_type}
    )


async def test_full_flow_kg_counter_with_level_sensor(hass: HomeAssistant) -> None:
    """The assistant suggests the measured level as start stock."""
    hass.states.async_set("sensor.silo_level", "50", {"unit_of_measurement": "%"})
    result = await _start(hass, "  Pelletsilo  ", "kg_counter")
    assert result["step_id"] == "source_kg_counter"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "source_entity": "sensor.boiler_usage_today",
            "calorific_value": 4.8,
            "max_step_kg": 10,
        },
    )
    assert result["step_id"] == "storage"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "capacity_kg": 6000,
            "min_stock_percent": 10,
            "level_entity": "sensor.silo_level",
        },
    )
    assert result["step_id"] == "start"
    schema = result["data_schema"].schema
    defaults = {str(k): k.default() for k in schema}
    assert defaults["initial_stock_kg"] == 3000
    assert defaults["import_history"] is True

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"initial_stock_kg": 3000, "initial_price_per_tonne": 420}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Pelletsilo"
    assert result["data"]["level_entity"] == "sensor.silo_level"
    assert result["data"]["source_type"] == "kg_counter"
    assert result["data"]["import_history"] is True


async def test_flow_energy_and_runtime_steps(hass: HomeAssistant) -> None:
    """Each source type shows its own form."""
    result = await _start(hass, "A", "energy_counter")
    assert result["step_id"] == "source_energy_counter"
    assert "efficiency" in {str(k) for k in result["data_schema"].schema}

    result = await _start(hass, "B", "runtime")
    assert result["step_id"] == "source_runtime"
    assert "kg_per_hour" in {str(k) for k in result["data_schema"].schema}


async def test_flow_without_level_sensor(hass: HomeAssistant) -> None:
    """The fill level sensor is optional."""
    result = await _start(hass, "Sacklager", "runtime")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "source_entity": "binary_sensor.burner",
            "calorific_value": 4.8,
            "kg_per_hour": 2.5,
            "max_step_kg": 10,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"capacity_kg": 1000, "min_stock_percent": 15}
    )
    # An on/off burner has no statistics, so there is nothing to take over.
    assert "import_history" not in {str(k) for k in result["data_schema"].schema}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"initial_stock_kg": 500, "initial_price_per_tonne": 0}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "level_entity" not in result["data"]


async def test_duplicate_name_aborts(hass: HomeAssistant, mock_entry) -> None:
    """Two storages with the same name are not allowed."""
    mock_entry.add_to_hass(hass)
    result = await _start(hass, "Pelletsilo", "kg_counter")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_changes_settings(hass: HomeAssistant, mock_entry) -> None:
    """Settings can be changed later; the entry reloads."""
    hass.states.async_set(
        "sensor.boiler_usage_today", "0", {"unit_of_measurement": "kg"}
    )
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"source_type": "kg_counter"}
    )
    assert result["step_id"] == "source_kg_counter"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "source_entity": "sensor.boiler_usage_today",
            "calorific_value": 5.0,
            "max_step_kg": 5,
        },
    )
    assert result["step_id"] == "storage"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"capacity_kg": 6200, "min_stock_percent": 20}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert mock_entry.options["capacity_kg"] == 6200
    assert mock_entry.runtime_data.min_stock_kg == 1240
    assert mock_entry.runtime_data.model.stock_kg == 5000
