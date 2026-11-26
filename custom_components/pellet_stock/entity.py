"""Base entity for Pellet Stock Manager."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription

from .const import DOMAIN
from .manager import PelletStockManager


class PelletStockEntity(Entity):
    """Entity that belongs to one pellet storage device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, manager: PelletStockManager, description: EntityDescription
    ) -> None:
        """Initialize."""
        self.manager = manager
        self.entity_description = description
        entry = manager.entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Pellet Stock Manager",
            model="Pellet storage",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Update when the manager changes."""
        self.async_on_remove(self.manager.async_add_listener(self.async_write_ha_state))
