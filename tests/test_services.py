"""Tests for the actions add_delivery, correct_stock and delete_delivery."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "pellet_stock"


@pytest.fixture(autouse=True)
def _german(hass: HomeAssistant) -> None:
    hass.config.language = "de"
    hass.config.currency = "EUR"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    hass.states.async_set(
        "sensor.boiler_usage_today", "0", {"unit_of_measurement": "kg"}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _call(hass: HomeAssistant, service: str, **data):
    return await hass.services.async_call(
        DOMAIN, service, data, blocking=True, return_response=True
    )


async def test_add_delivery_updates_stock_and_price(
    hass: HomeAssistant, mock_entry, hass_storage
) -> None:
    """A delivery raises the stock, mixes the price and is saved at once."""
    await _setup(hass, mock_entry)
    resp = await _call(
        hass,
        "add_delivery",
        config_entry_id=mock_entry.entry_id,
        kg=1000,
        price=500,
        date="2026-11-20",
        note="Lieferant X",
    )
    assert resp["stock_kg"] == 6000
    assert hass.states.get("sensor.pelletsilo_bestand").state == "6000.0"
    # (5000 kg * 0.40 + 500) / 6000 kg = 0.41667 per kg
    assert (
        hass.states.get("sensor.pelletsilo_durchschnittspreis_pro_tonne").state
        == "416.67"
    )
    last = hass.states.get("sensor.pelletsilo_letzte_lieferung")
    assert last.state.startswith("2026-11-2")
    assert last.attributes["kg"] == 1000
    assert last.attributes["deliveries"][0]["id"] == resp["delivery_id"]
    stored = hass_storage[f"pellet_stock.{mock_entry.entry_id}"]["data"]
    assert stored["deliveries"][0]["kg"] == 1000


async def test_delete_delivery_reverses_it(hass: HomeAssistant, mock_entry) -> None:
    """Deleting a delivery takes kg and value back out."""
    await _setup(hass, mock_entry)
    resp = await _call(
        hass, "add_delivery", config_entry_id=mock_entry.entry_id, kg=1000, price=500
    )
    resp = await _call(
        hass,
        "delete_delivery",
        config_entry_id=mock_entry.entry_id,
        delivery_id=resp["delivery_id"],
    )
    assert resp == {"deleted_kg": 1000, "stock_kg": 5000}
    assert (
        hass.states.get("sensor.pelletsilo_durchschnittspreis_pro_tonne").state
        == "400.0"
    )
    assert hass.states.get("sensor.pelletsilo_letzte_lieferung").state == "unknown"

    with pytest.raises(ServiceValidationError):
        await _call(
            hass,
            "delete_delivery",
            config_entry_id=mock_entry.entry_id,
            delivery_id="nope",
        )


async def test_correct_stock(hass: HomeAssistant, mock_entry) -> None:
    """The stock can be set to a measured value."""
    await _setup(hass, mock_entry)
    resp = await _call(
        hass, "correct_stock", config_entry_id=mock_entry.entry_id, stock_kg=4800
    )
    assert resp == {"difference_kg": -200}
    assert hass.states.get("sensor.pelletsilo_bestand").state == "4800.0"


async def test_delivery_clears_low_stock(hass: HomeAssistant, entry_data) -> None:
    """After a delivery the minimum stock warning goes off again."""
    entry_data["initial_stock_kg"] = 100
    entry = MockConfigEntry(domain=DOMAIN, title="Pelletsilo", data=entry_data)
    await _setup(hass, entry)
    binary = "binary_sensor.pelletsilo_mindestbestand_erreicht"
    assert hass.states.get(binary).state == "on"
    await _call(hass, "add_delivery", config_entry_id=entry.entry_id, kg=3000)
    assert hass.states.get(binary).state == "off"


async def test_unknown_or_unloaded_storage(hass: HomeAssistant, mock_entry) -> None:
    """Clear errors for a wrong or unloaded storage."""
    await _setup(hass, mock_entry)
    with pytest.raises(ServiceValidationError):
        await _call(hass, "correct_stock", config_entry_id="missing", stock_kg=1)
    await hass.config_entries.async_unload(mock_entry.entry_id)
    with pytest.raises(ServiceValidationError):
        await _call(
            hass, "correct_stock", config_entry_id=mock_entry.entry_id, stock_kg=1
        )
