"""Tests for taking over history from the Home Assistant statistics."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.pellet_stock.const import DOMAIN

USAGE = "sensor.boiler_usage_today"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Start the recorder before Home Assistant, then allow custom integrations."""
    return


def _day_start(days_ago: int):
    return dt_util.start_of_local_day(dt_util.now().date() - timedelta(days=days_ago))


def _import_daily_counter(hass: HomeAssistant, per_day: dict[int, float]) -> None:
    """Hourly statistics of a counter that resets every midnight (measurement)."""
    rows = []
    for days_ago, total in per_day.items():
        start = _day_start(days_ago)
        for hour in range(24):
            value = total * (hour + 1) / 24
            rows.append(
                {
                    "start": start + timedelta(hours=hour),
                    "mean": value,
                    "min": 0.0 if hour == 0 else total * hour / 24,
                    "max": value,
                }
            )
    async_import_statistics(
        hass,
        {
            "mean_type": StatisticMeanType.ARITHMETIC,
            "has_sum": False,
            "name": None,
            "source": "recorder",
            "statistic_id": USAGE,
            "unit_class": "mass",
            "unit_of_measurement": "kg",
        },
        rows,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_daily_counter_history_is_imported(
    recorder_mock: Recorder, hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Daily maxima of a resetting counter become the daily consumption."""
    hass.config.language = "de"
    _import_daily_counter(hass, {3: 24.0, 2: 30.0, 400 + 30: 12.0})
    await async_wait_recording_done(hass)
    hass.states.async_set(USAGE, "0", {"unit_of_measurement": "kg"})
    await _setup(hass, mock_entry)
    manager = mock_entry.runtime_data

    result = await hass.services.async_call(
        DOMAIN,
        "import_history",
        {"config_entry_id": mock_entry.entry_id},
        blocking=True,
        return_response=True,
    )
    assert result["status"] == "imported"
    assert result["days"] == 3
    assert result["method"] == "daily_max"
    assert result["kg"] == pytest.approx(66.0)

    model = manager.model
    assert model.stock_kg == 5000  # stock untouched
    assert model.consumed_on(_day_start(2).date()) == pytest.approx(30.0)
    # Older than the 400 kept days: only in the monthly totals.
    old = _day_start(430).date()
    assert old.isoformat() not in model.daily_kg
    assert model.kg_by_month[old.isoformat()[:7]] >= 12.0
    # 400 € per tonne from the setup.
    assert model.daily_cost[_day_start(2).date().isoformat()] == pytest.approx(12.0)
    assert model.history_from == old.isoformat()
    # The range can use the imported full days right away.
    assert manager.estimate().basis == "full_days"
    reason = hass.states.get("sensor.pelletsilo_gesamtverbrauch").attributes["reason"]
    assert "3 Tage" in reason

    # A second import is refused, so nothing is counted twice.
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "import_history",
            {"config_entry_id": mock_entry.entry_id},
            blocking=True,
            return_response=True,
        )


async def test_total_counter_uses_daily_change(
    recorder_mock: Recorder, hass: HomeAssistant, entry_data
) -> None:
    """A running kWh total uses the daily change, converted to kg."""
    entry_data.update(
        source_type="energy_counter", source_entity="sensor.heat", efficiency=100
    )
    rows = []
    total = 0.0
    for days_ago in (3, 2):
        start = _day_start(days_ago)
        for hour in range(24):
            total += 4.8  # 1 kg per hour
            rows.append(
                {"start": start + timedelta(hours=hour), "state": total, "sum": total}
            )
    async_import_statistics(
        hass,
        {
            "mean_type": StatisticMeanType.NONE,
            "has_sum": True,
            "name": None,
            "source": "recorder",
            "statistic_id": "sensor.heat",
            "unit_class": "energy",
            "unit_of_measurement": "kWh",
        },
        rows,
    )
    await async_wait_recording_done(hass)
    entry = MockConfigEntry(domain=DOMAIN, title="Pelletsilo", data=entry_data)
    hass.states.async_set("sensor.heat", str(total), {"unit_of_measurement": "kWh"})
    await _setup(hass, entry)

    result = await entry.runtime_data.async_import_history()
    assert result.status == "imported"
    assert result.method == "change"
    # The first day has no change to a previous day: only the second counts.
    assert entry.runtime_data.model.consumed_on(_day_start(2).date()) == pytest.approx(
        24.0
    )


async def test_import_runs_once_after_setup(
    recorder_mock: Recorder, hass: HomeAssistant, entry_data
) -> None:
    """With the setup option, the history is taken over automatically."""
    _import_daily_counter(hass, {2: 20.0})
    await async_wait_recording_done(hass)
    entry_data["import_history"] = True
    entry = MockConfigEntry(domain=DOMAIN, title="Pelletsilo", data=entry_data)
    hass.states.async_set(USAGE, "0", {"unit_of_measurement": "kg"})
    await _setup(hass, entry)
    await hass.async_block_till_done(wait_background_tasks=True)
    model = entry.runtime_data.model
    assert model.consumed_on(_day_start(2).date()) == pytest.approx(20.0)
    assert model.history_checked


async def test_no_statistics(recorder_mock: Recorder, hass: HomeAssistant, mock_entry):
    """Without statistics nothing happens and the reason says why."""
    hass.config.language = "en"
    hass.states.async_set(USAGE, "0", {"unit_of_measurement": "kg"})
    await _setup(hass, mock_entry)
    result = await mock_entry.runtime_data.async_import_history()
    assert result.status == "no_statistics"
    assert not mock_entry.runtime_data.model.history_from
