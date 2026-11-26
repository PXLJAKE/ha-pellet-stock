"""Button: take the fill level sensor value as stock."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PelletStockConfigEntry
from .const import DOMAIN
from .entity import PelletStockEntity

ADOPT_LEVEL = ButtonEntityDescription(
    key="adopt_level",
    translation_key="adopt_level",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PelletStockConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the button only when a fill level sensor is configured."""
    if entry.runtime_data.level_entity:
        async_add_entities([AdoptLevelButton(entry.runtime_data, ADOPT_LEVEL)])


class AdoptLevelButton(PelletStockEntity, ButtonEntity):
    """Set the stock to the measured fill level."""

    async def async_press(self) -> None:
        """Adopt the measured value."""
        if not self.manager.async_adopt_level():
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="level_unavailable"
            )
