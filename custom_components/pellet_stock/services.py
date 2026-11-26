"""Actions (services) for Pellet Stock Manager."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN
from .manager import PelletStockManager

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_KG = "kg"
ATTR_PRICE = "price"
ATTR_DATE = "date"
ATTR_NOTE = "note"
ATTR_STOCK_KG = "stock_kg"
ATTR_DELIVERY_ID = "delivery_id"

SERVICE_ADD_DELIVERY = "add_delivery"
SERVICE_CORRECT_STOCK = "correct_stock"
SERVICE_DELETE_DELIVERY = "delete_delivery"

# Same upper limit as the storage capacity in the setup assistant.
MAX_KG = 100_000

_ENTRY = {vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string}

ADD_DELIVERY_SCHEMA = vol.Schema(
    {
        **_ENTRY,
        vol.Required(ATTR_KG): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=MAX_KG)
        ),
        vol.Optional(ATTR_PRICE, default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=100_000)
        ),
        vol.Optional(ATTR_DATE): cv.date,
        vol.Optional(ATTR_NOTE, default=""): vol.All(cv.string, vol.Length(max=200)),
    }
)
CORRECT_STOCK_SCHEMA = vol.Schema(
    {
        **_ENTRY,
        vol.Required(ATTR_STOCK_KG): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=MAX_KG)
        ),
    }
)
DELETE_DELIVERY_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Required(ATTR_DELIVERY_ID): cv.string}
)


def _manager(hass: HomeAssistant, call: ServiceCall) -> PelletStockManager:
    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="unknown_storage"
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="storage_not_loaded"
        )
    return entry.runtime_data


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions once for all storages."""

    async def add_delivery(call: ServiceCall) -> ServiceResponse:
        manager = _manager(hass, call)
        day = call.data.get(ATTR_DATE) or dt_util.now().date()
        delivery = await manager.async_add_delivery(
            call.data[ATTR_KG], call.data[ATTR_PRICE], day, call.data[ATTR_NOTE]
        )
        return {
            "delivery_id": delivery.id,
            "stock_kg": round(manager.model.stock_kg, 1),
        }

    async def correct_stock(call: ServiceCall) -> ServiceResponse:
        manager = _manager(hass, call)
        diff = await manager.async_correct_stock(call.data[ATTR_STOCK_KG])
        return {"difference_kg": round(diff, 1)}

    async def delete_delivery(call: ServiceCall) -> ServiceResponse:
        manager = _manager(hass, call)
        delivery = await manager.async_delete_delivery(call.data[ATTR_DELIVERY_ID])
        if delivery is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="unknown_delivery"
            )
        result: dict[str, Any] = {
            "deleted_kg": delivery.kg,
            "stock_kg": round(manager.model.stock_kg, 1),
        }
        return result

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_DELIVERY,
        add_delivery,
        schema=ADD_DELIVERY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CORRECT_STOCK,
        correct_stock,
        schema=CORRECT_STOCK_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_DELIVERY,
        delete_delivery,
        schema=DELETE_DELIVERY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
