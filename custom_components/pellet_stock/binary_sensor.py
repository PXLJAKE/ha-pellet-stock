"""Binary sensor: minimum stock reached."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PelletStockConfigEntry
from .entity import PelletStockEntity

LOW_STOCK = BinarySensorEntityDescription(
    key="low_stock",
    translation_key="low_stock",
    device_class=BinarySensorDeviceClass.PROBLEM,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PelletStockConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor."""
    async_add_entities([LowStockBinarySensor(entry.runtime_data, LOW_STOCK)])


class LowStockBinarySensor(PelletStockEntity, BinarySensorEntity):
    """On when the stock is below the minimum."""

    _unrecorded_attributes = frozenset({"reason"})

    @property
    def is_on(self) -> bool:
        """Return true when the stock is low."""
        return self.manager.low_stock

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Explain the state."""
        return {
            "reason": self.manager.low_stock_reason(),
            "min_stock_kg": round(self.manager.min_stock_kg, 1),
        }
