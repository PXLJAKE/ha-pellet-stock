"""Sensors for Pellet Stock Manager."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import PelletStockConfigEntry
from .entity import PelletStockEntity
from .manager import PelletStockManager


def _round(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def _fill_percent(m: PelletStockManager) -> float | None:
    if m.capacity_kg <= 0:
        return None
    return round(min(100.0, m.model.stock_kg / m.capacity_kg * 100), 1)


@dataclass(frozen=True, kw_only=True)
class PelletSensorDescription(SensorEntityDescription):
    """Describes one pellet sensor."""

    value_fn: Callable[[PelletStockManager], float | None]
    attrs_fn: Callable[[PelletStockManager], dict[str, Any]] | None = None
    reset_fn: Callable[[], datetime] | None = None
    currency: bool = False
    per_kwh: bool = False


def _month_start() -> datetime:
    return dt_util.start_of_local_day().replace(day=1)


def _year_start() -> datetime:
    return dt_util.start_of_local_day().replace(month=1, day=1)


def _source_attrs(m: PelletStockManager) -> dict[str, Any]:
    if m.last_decision is None:
        return {}
    return {
        "reason": m.last_decision.reason,
        "reason_time": m.last_decision.at.isoformat(),
    }


SENSORS: tuple[PelletSensorDescription, ...] = (
    PelletSensorDescription(
        key="stock",
        translation_key="stock",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda m: _round(m.model.stock_kg, 1),
    ),
    PelletSensorDescription(
        key="fill_level",
        translation_key="fill_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_fill_percent,
    ),
    PelletSensorDescription(
        key="range",
        translation_key="range",
        native_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda m: _round(m.estimate().days, 1),
        attrs_fn=lambda m: {"reason": m.range_reason()},
    ),
    PelletSensorDescription(
        key="avg_daily_consumption",
        translation_key="avg_daily_consumption",
        native_unit_of_measurement="kg/d",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda m: _round(m.estimate().avg_kg_per_day, 2),
    ),
    PelletSensorDescription(
        key="consumption_today",
        translation_key="consumption_today",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=lambda m: _round(m.model.consumed_on(dt_util.now().date()), 2),
        reset_fn=dt_util.start_of_local_day,
    ),
    PelletSensorDescription(
        key="consumption_total",
        translation_key="consumption_total",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda m: _round(m.model.total_consumed_kg, 2),
        attrs_fn=_source_attrs,
    ),
    PelletSensorDescription(
        key="energy_total",
        translation_key="energy_total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda m: _round(m.model.total_consumed_kg * m.calorific_value, 2),
    ),
    PelletSensorDescription(
        key="price_per_kwh",
        translation_key="price_per_kwh",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=lambda m: _round(m.price_per_kwh(), 5),
        per_kwh=True,
    ),
    PelletSensorDescription(
        key="price_per_tonne",
        translation_key="price_per_tonne",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda m: (
            _round(m.model.avg_price_per_kg * 1000, 2)
            if m.model.avg_price_per_kg > 0
            else None
        ),
        currency=True,
    ),
    PelletSensorDescription(
        key="cost_month",
        translation_key="cost_month",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda m: _round(m.cost_this_month(), 2),
        reset_fn=_month_start,
        currency=True,
    ),
    PelletSensorDescription(
        key="cost_year",
        translation_key="cost_year",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda m: _round(m.cost_this_year(), 2),
        reset_fn=_year_start,
        currency=True,
    ),
)

LEVEL_DEVIATION = PelletSensorDescription(
    key="level_deviation",
    translation_key="level_deviation",
    native_unit_of_measurement=UnitOfMass.KILOGRAMS,
    device_class=SensorDeviceClass.WEIGHT,
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    suggested_display_precision=0,
    value_fn=lambda m: _round(m.level_deviation_kg(), 1),
    attrs_fn=lambda m: {"measured_kg": _round(m.level_kg(), 1)},
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PelletStockConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    manager = entry.runtime_data
    descriptions = list(SENSORS)
    if manager.level_entity:
        descriptions.append(LEVEL_DEVIATION)
    async_add_entities(PelletSensor(manager, d) for d in descriptions)


class PelletSensor(PelletStockEntity, SensorEntity):
    """A value of the pellet storage."""

    entity_description: PelletSensorDescription
    _unrecorded_attributes = frozenset({"reason", "reason_time", "measured_kg"})

    def __init__(
        self, manager: PelletStockManager, description: PelletSensorDescription
    ) -> None:
        """Initialize."""
        super().__init__(manager, description)
        currency = manager.hass.config.currency
        if description.currency:
            self._attr_native_unit_of_measurement = (
                f"{currency}/t" if description.key == "price_per_tonne" else currency
            )
        if description.per_kwh:
            self._attr_native_unit_of_measurement = (
                f"{currency}/{UnitOfEnergy.KILO_WATT_HOUR}"
            )

    @property
    def native_value(self) -> float | None:
        """Return the value."""
        return self.entity_description.value_fn(self.manager)

    @property
    def last_reset(self) -> datetime | None:
        """Return the start of the current period for period totals."""
        if self.entity_description.reset_fn is None:
            return None
        return self.entity_description.reset_fn()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return explanations."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.manager)
