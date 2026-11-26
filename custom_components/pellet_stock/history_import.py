"""Take over past consumption from the Home Assistant long-term statistics.

Home Assistant keeps hourly statistics of sensors with a state class for
years. They are read once, turned into daily consumption and added to the
history of the storage, so the charts are filled from the first day. The
stock is not changed.

- Counters with a running total (state class total / total_increasing):
  the daily change is the consumption.
- Counters that reset every day but are recorded as measurement (like many
  boiler integrations): the highest value of the day is the consumption.
- Other measurements: highest minus lowest value of the day.
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
    method: str = ""  # "change", "daily_max", "max_minus_min"

    def as_dict(self) -> dict[str, Any]:
        """Return the result as a service response."""
        return {
            "status": self.status,
            "days": self.days,
            "kg": round(self.kg, 1),
            "first_day": self.first_day,
            "method": self.method,
        }


def _daily_kg(
    row: dict[str, Any], has_sum: bool, max_step: float
) -> tuple[float | None, str]:
    """Return the consumption of one day in source units and the method used."""
    if has_sum:
        return row.get("change"), "change"
    high, low = row.get("max"), row.get("min")
    if high is None:
        return None, ""
    if low is not None and low > max_step:
        # Never close to zero on this day: not a daily counter.
        return high - low, "max_minus_min"
    return high, "daily_max"


async def _async_daily_rows(
    hass: HomeAssistant, statistic_id: str, first_tracked_day: date
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Return the daily statistics rows, whether they have a sum, and the unit."""
    if "recorder" not in hass.config.components:
        return [], False, None
    recorder = get_instance(hass)
    metadata = await recorder.async_add_executor_job(
        lambda: get_metadata(hass, statistic_ids={statistic_id})
    )
    if statistic_id not in metadata:
        return [], False, None
    meta = metadata[statistic_id][1]
    has_sum = bool(meta["has_sum"])
    start = dt_util.start_of_local_day(
        first_tracked_day - timedelta(days=365 * MAX_YEARS)
    )
    end = dt_util.start_of_local_day(first_tracked_day + timedelta(days=1))
    types: set[Any] = {"change"} if has_sum else {"max", "min"}
    rows = await recorder.async_add_executor_job(
        lambda: statistics_during_period(
            hass, start, end, {statistic_id}, "day", None, types
        )
    )
    return list(rows.get(statistic_id, [])), has_sum, meta["unit_of_measurement"]


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
    daily, has_sum, unit = await _async_daily_rows(
        manager.hass, statistic_id, first_tracked_day
    )
    if not daily:
        return ImportResult("no_statistics")

    today = dt_util.now().date()
    keep_from = today - timedelta(days=HISTORY_DAYS)
    result = ImportResult("imported")
    for row in daily:
        day = dt_util.as_local(dt_util.utc_from_timestamp(row["start"])).date()
        if day > first_tracked_day:
            continue
        value, method = _daily_kg(row, has_sum, manager.max_step_kg)
        if value is None or value <= 0:
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
        result.method = result.method or method
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
