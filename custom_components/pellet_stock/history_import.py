"""Take over past consumption from the Home Assistant long-term statistics.

Home Assistant keeps hourly statistics of sensors with a state class for
years. They are read once, turned into daily consumption and added to the
history of the storage, so the charts are filled from the first day. The
stock is not changed.

- Counters with a running total (state class total / total_increasing):
  the daily change is the consumption.
- Sensors recorded as measurement (like the daily counters of many boiler
  integrations): the hourly lowest and highest values are followed like a
  counter. Every rise is consumption, and a drop is a reset. The daily
  highest value alone would be wrong: in the first hour after midnight it
  still holds the total of the day before.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    get_metadata,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import CONF_SOURCE_ENTITY, HISTORY_DAYS

if TYPE_CHECKING:
    from .manager import PelletStockManager

_LOGGER = logging.getLogger(__name__)

# Days with more than this are treated as faulty statistics and skipped.
MAX_KG_PER_DAY = 500.0
# How far back the statistics are read.
MAX_YEARS = 10


@dataclass(slots=True)
class ImportResult:
    """Outcome of a history import ("Why?")."""

    status: str  # "imported", "no_statistics", "already_imported", "not_sensor"
    days: int = 0
    kg: float = 0.0
    first_day: str | None = None
    method: str = ""  # "change" (running total) or "hourly" (measurement)

    def as_dict(self) -> dict[str, Any]:
        """Return the result as a service response."""
        return {
            "status": self.status,
            "days": self.days,
            "kg": round(self.kg, 1),
            "first_day": self.first_day,
            "method": self.method,
        }


# One hour of statistics: local start, lowest and highest value.
type HourRow = tuple[datetime, float, float]


def hourly_to_daily(rows: list[HourRow]) -> dict[date, float]:
    """Follow hourly lowest/highest values like a counter, summed per day.

    Without a reset, a counter ends the hour at its highest value. In an hour
    with a reset (the lowest value is at most half of where the hour before
    ended), the highest value may still be the old total, so the value after
    the reset is taken from the lowest value of the next hour.
    """
    daily: dict[date, float] = {}
    previous_end: float | None = None
    for index, (start, low, high) in enumerate(rows):
        next_low: float | None = None
        if index + 1 < len(rows) and rows[index + 1][0] - start == timedelta(hours=1):
            next_low = rows[index + 1][1]
        after = min(next_low, high) if next_low is not None else None
        if previous_end is None:
            # First hour: only the rise that is certain.
            end = after if after is not None else high
            gain = end - low
        elif previous_end > 0 and low <= previous_end / 2:
            # Reset in this hour.
            end = after
            if end is None:
                end = low if high >= previous_end else high
            before_reset = max(0.0, high - previous_end) if end < high else 0.0
            gain = before_reset + end
        else:
            end = high
            gain = high - previous_end
        if gain > 0:
            day = start.date()
            daily[day] = daily.get(day, 0.0) + gain
        previous_end = end
    return daily


def _read_days(
    hass: HomeAssistant, statistic_id: str, first_tracked_day: date, has_sum: bool
) -> dict[date, float]:
    """Read the statistics and return the consumption per day (executor)."""
    end = dt_util.start_of_local_day(first_tracked_day + timedelta(days=1))
    oldest = end - timedelta(days=365 * MAX_YEARS)
    if has_sum:
        rows = statistics_during_period(
            hass, oldest, end, {statistic_id}, "day", None, {"change"}
        ).get(statistic_id, [])
        return {
            dt_util.as_local(dt_util.utc_from_timestamp(row["start"])).date(): change
            for row in rows
            if (change := row.get("change")) is not None
        }
    hours: list[HourRow] = []
    start = oldest
    while start < end:
        # A year at a time keeps the memory use low on small machines.
        stop = min(end, start + timedelta(days=365))
        for row in statistics_during_period(
            hass, start, stop, {statistic_id}, "hour", None, {"max", "min"}
        ).get(statistic_id, []):
            if row.get("min") is not None and row.get("max") is not None:
                hours.append(
                    (
                        dt_util.as_local(dt_util.utc_from_timestamp(row["start"])),
                        row["min"],
                        row["max"],
                    )
                )
        start = stop
    return hourly_to_daily(hours)


async def _async_daily_values(
    hass: HomeAssistant, statistic_id: str, first_tracked_day: date
) -> tuple[dict[date, float], str, str | None]:
    """Return the consumption per day in source units, the method and the unit."""
    if "recorder" not in hass.config.components:
        return {}, "", None
    recorder = get_instance(hass)
    metadata = await recorder.async_add_executor_job(
        lambda: get_metadata(hass, statistic_ids={statistic_id})
    )
    if statistic_id not in metadata:
        return {}, "", None
    meta = metadata[statistic_id][1]
    has_sum = bool(meta["has_sum"])
    days = await recorder.async_add_executor_job(
        _read_days, hass, statistic_id, first_tracked_day, has_sum
    )
    return days, "change" if has_sum else "hourly", meta["unit_of_measurement"]


async def async_import_history(manager: PelletStockManager) -> ImportResult:
    """Read the statistics of the source sensor and fill the history once."""
    model = manager.model
    if model.history_from:
        return ImportResult("already_imported", first_day=model.history_from)
    statistic_id: str = manager.config[CONF_SOURCE_ENTITY]
    if not statistic_id.startswith("sensor."):
        return ImportResult("not_sensor")

    started = (
        datetime.fromisoformat(model.tracking_since)
        if model.tracking_since
        else dt_util.now()
    )
    first_tracked_day = started.date()
    daily, method, unit = await _async_daily_values(
        manager.hass, statistic_id, first_tracked_day
    )
    if not daily:
        return ImportResult("no_statistics")

    today = dt_util.now().date()
    keep_from = today - timedelta(days=HISTORY_DAYS)
    result = ImportResult("imported", method=method)
    for day in sorted(daily):
        value = daily[day]
        if day > first_tracked_day or value <= 0:
            continue
        kg = manager.value_to_kg(value, unit)
        if day == first_tracked_day:
            # Part of this day was already counted by the integration.
            kg -= model.consumed_on(day)
        if kg <= 0 or kg > MAX_KG_PER_DAY:
            continue
        model.import_day(day, kg, keep_daily=day >= keep_from)
        result.days += 1
        result.kg += kg
    if not result.days:
        return ImportResult("no_statistics")
    result.first_day = model.history_from
    _LOGGER.debug(
        "Imported %s days (%.1f kg) for %s using %s",
        result.days,
        result.kg,
        statistic_id,
        result.method,
    )
    return result
