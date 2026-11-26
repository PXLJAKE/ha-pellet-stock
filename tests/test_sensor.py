"""Tests for the storage behaviour seen through the entities."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.pellet_stock.const import DOMAIN, EVENT_LOW_STOCK

KG = {"unit_of_measurement": "kg"}
USAGE = "sensor.boiler_usage_today"


def _state(hass: HomeAssistant, key: str) -> str:
    return hass.states.get(f"sensor.pelletsilo_{key}").state


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture(autouse=True)
def _german(hass: HomeAssistant) -> None:
    hass.config.language = "de"
    hass.config.currency = "EUR"


async def test_kg_counter_updates_stock_cost_and_energy(
    hass: HomeAssistant, mock_entry
) -> None:
    """A daily kg counter lowers the stock; cost and energy follow."""
    hass.states.async_set(USAGE, "10", KG)
    await _setup(hass, mock_entry)
    assert _state(hass, "bestand") == "5000.0"

    hass.states.async_set(USAGE, "13", KG)
    await hass.async_block_till_done()
    assert _state(hass, "bestand") == "4997.0"
    assert _state(hass, "gesamtverbrauch") == "3.0"
    assert _state(hass, "verbrauch_heute") == "3.0"
    assert _state(hass, "energie") == "14.4"
    assert _state(hass, "kosten_diesen_monat") == "1.2"
    assert _state(hass, "kosten_dieses_jahr") == "1.2"
    assert _state(hass, "preis_pro_kwh") == str(round(0.4 / 4.8, 5))
    assert _state(hass, "durchschnittspreis_pro_tonne") == "400.0"
    assert _state(hass, "fullgrad") == "83.3"

    total = hass.states.get("sensor.pelletsilo_gesamtverbrauch")
    assert "3.00 kg" in total.attributes["reason"]
    assert (
        hass.states.get("sensor.pelletsilo_energie").attributes["unit_of_measurement"]
        == "kWh"
    )
    assert (
        hass.states.get("sensor.pelletsilo_preis_pro_kwh").attributes[
            "unit_of_measurement"
        ]
        == "EUR/kWh"
    )


async def test_unavailable_and_spikes_are_ignored(
    hass: HomeAssistant, mock_entry
) -> None:
    """Unavailable values and implausible jumps never change the stock."""
    hass.states.async_set(USAGE, "10", KG)
    await _setup(hass, mock_entry)
    hass.states.async_set(USAGE, "unavailable", KG)
    await hass.async_block_till_done()
    hass.states.async_set(USAGE, "60", KG)
    await hass.async_block_till_done()
    assert _state(hass, "bestand") == "5000.0"
    reason = hass.states.get("sensor.pelletsilo_gesamtverbrauch").attributes["reason"]
    assert "ignoriert" in reason


async def test_low_stock_event_and_binary_sensor(
    hass: HomeAssistant, entry_data
) -> None:
    """Crossing the minimum fires one event and turns the sensor on."""
    entry_data["initial_stock_kg"] = 605
    entry = MockConfigEntry(domain=DOMAIN, title="Pelletsilo", data=entry_data)
    events = async_capture_events(hass, EVENT_LOW_STOCK)
    hass.states.async_set(USAGE, "0", KG)
    await _setup(hass, entry)
    binary = "binary_sensor.pelletsilo_mindestbestand_erreicht"
    assert hass.states.get(binary).state == "off"

    hass.states.async_set(USAGE, "8", KG)
    await hass.async_block_till_done()
    hass.states.async_set(USAGE, "9", KG)
    await hass.async_block_till_done()
    assert hass.states.get(binary).state == "on"
    assert len(events) == 1
    assert events[0].data["stock_kg"] == 597
    assert "unter dem Mindestbestand" in events[0].data["reason"]
    assert "unter dem Mindestbestand" in hass.states.get(binary).attributes["reason"]


async def test_range_after_full_days(
    hass: HomeAssistant, mock_entry, freezer: FrozenDateTimeFactory
) -> None:
    """The range appears from real consumption and explains itself."""
    freezer.move_to(dt_util.start_of_local_day() + timedelta(hours=1))
    hass.states.async_set(USAGE, "0", KG)
    await _setup(hass, mock_entry)
    assert _state(hass, "reichweite") == "unknown"

    for day in range(3):
        freezer.tick(timedelta(hours=10))
        for value in ("8", "16", "20"):
            hass.states.async_set(USAGE, value, KG)
            await hass.async_block_till_done()
        # next midnight: counter resets
        freezer.move_to(dt_util.start_of_local_day() + timedelta(days=1, seconds=10))
        async_fire_time_changed(hass)
        hass.states.async_set(USAGE, "0", KG)
        await hass.async_block_till_done()
        _ = day

    # Day 1 was partial; days 2 and 3 are full days with 20 kg each.
    assert _state(hass, "durchschnittlicher_tagesverbrauch") == "20.0"
    assert _state(hass, "reichweite") == str(round(4940 / 20, 1))
    reason = hass.states.get("sensor.pelletsilo_reichweite").attributes["reason"]
    assert "2 vollen Tagen" in reason


async def test_runtime_source_counts_burner_hours(
    hass: HomeAssistant, entry_data, freezer: FrozenDateTimeFactory
) -> None:
    """An on/off burner entity is turned into kg via kg per hour."""
    entry_data.update(
        source_type="runtime", source_entity="binary_sensor.burner", kg_per_hour=2.0
    )
    entry = MockConfigEntry(domain=DOMAIN, title="Pelletsilo", data=entry_data)
    hass.states.async_set("binary_sensor.burner", "off")
    await _setup(hass, entry)
    hass.states.async_set("binary_sensor.burner", "on")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=90))
    hass.states.async_set("binary_sensor.burner", "off")
    await hass.async_block_till_done()
    assert _state(hass, "gesamtverbrauch") == "3.0"


async def test_energy_source_converts_kwh(hass: HomeAssistant, entry_data) -> None:
    """kWh are turned into kg with calorific value and efficiency."""
    entry_data.update(
        source_type="energy_counter",
        source_entity="sensor.heat",
        efficiency=90,
        calorific_value=5.0,
    )
    entry = MockConfigEntry(domain=DOMAIN, title="Pelletsilo", data=entry_data)
    attrs = {"unit_of_measurement": "kWh"}
    hass.states.async_set("sensor.heat", "1000", attrs)
    await _setup(hass, entry)
    hass.states.async_set("sensor.heat", "1036", attrs)
    await hass.async_block_till_done()
    # 36 kWh heat / 0.9 = 40 kWh fuel / 5 kWh/kg = 8 kg
    assert _state(hass, "gesamtverbrauch") == "8.0"


async def test_level_sensor_deviation_and_adopt(
    hass: HomeAssistant, entry_data
) -> None:
    """A scale is compared and can be taken over with the button."""
    entry_data["level_entity"] = "sensor.scale"
    entry = MockConfigEntry(domain=DOMAIN, title="Pelletsilo", data=entry_data)
    hass.states.async_set("sensor.scale", "4.9", {"unit_of_measurement": "t"})
    hass.states.async_set(USAGE, "0", KG)
    await _setup(hass, entry)
    assert _state(hass, "abweichung_zum_messwert") == "100.0"

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.pelletsilo_gemessenen_fullstand_ubernehmen"},
        blocking=True,
    )
    assert _state(hass, "bestand") == "4900.0"
    assert _state(hass, "abweichung_zum_messwert") == "0.0"


async def test_stock_survives_reload(hass: HomeAssistant, mock_entry) -> None:
    """Stock and counter baseline are kept across a restart."""
    hass.states.async_set(USAGE, "10", KG)
    await _setup(hass, mock_entry)
    hass.states.async_set(USAGE, "15", KG)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert _state(hass, "bestand") == "4995.0"
    # consumption while HA was "down" is counted from the stored baseline
    hass.states.async_set(USAGE, "17", KG)
    await hass.async_block_till_done()
    assert _state(hass, "bestand") == "4993.0"
