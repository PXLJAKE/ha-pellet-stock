"""Setup assistant for Pellet Stock Manager.

Steps: name and consumption source, source details, storage, start values.
Every field has a plain-language help text (see strings.json).
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_CALORIFIC_VALUE,
    CONF_CAPACITY_KG,
    CONF_EFFICIENCY,
    CONF_IMPORT_HISTORY,
    CONF_INITIAL_PRICE_PER_TONNE,
    CONF_INITIAL_STOCK_KG,
    CONF_KG_PER_HOUR,
    CONF_LEVEL_ENTITY,
    CONF_MAX_STEP_KG,
    CONF_MIN_STOCK_PERCENT,
    CONF_SOURCE_ENTITY,
    CONF_SOURCE_TYPE,
    DEFAULT_CALORIFIC_VALUE,
    DEFAULT_CAPACITY_KG,
    DEFAULT_EFFICIENCY,
    DEFAULT_KG_PER_HOUR,
    DEFAULT_MAX_STEP_KG,
    DEFAULT_MIN_STOCK_PERCENT,
    DEFAULT_NAME,
    DEFAULT_PRICE_PER_TONNE,
    DOMAIN,
    SOURCE_ENERGY,
    SOURCE_KG,
    SOURCE_RUNTIME,
    SOURCE_TYPES,
)


def _number(
    minimum: float, maximum: float, step: float, unit: str | None = None
) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            unit_of_measurement=unit,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _source_type_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=SOURCE_TYPES,
            translation_key=CONF_SOURCE_TYPE,
            mode=selector.SelectSelectorMode.LIST,
        )
    )


def _source_schema(source_type: str, values: dict[str, Any]) -> vol.Schema:
    """Fields for the chosen consumption source."""
    fields: dict[Any, Any] = {}
    if source_type == SOURCE_KG:
        entity = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="weight")
        )
    elif source_type == SOURCE_ENERGY:
        entity = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )
    else:
        entity = selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["binary_sensor", "switch", "input_boolean", "sensor"]
            )
        )
    fields[
        vol.Required(
            CONF_SOURCE_ENTITY, default=values.get(CONF_SOURCE_ENTITY, vol.UNDEFINED)
        )
    ] = entity

    if source_type in (SOURCE_ENERGY, SOURCE_KG, SOURCE_RUNTIME):
        fields[
            vol.Required(
                CONF_CALORIFIC_VALUE,
                default=values.get(CONF_CALORIFIC_VALUE, DEFAULT_CALORIFIC_VALUE),
            )
        ] = _number(3.0, 6.0, 0.1, "kWh/kg")
    if source_type == SOURCE_ENERGY:
        fields[
            vol.Required(
                CONF_EFFICIENCY, default=values.get(CONF_EFFICIENCY, DEFAULT_EFFICIENCY)
            )
        ] = _number(50, 100, 1, "%")
    if source_type == SOURCE_RUNTIME:
        fields[
            vol.Required(
                CONF_KG_PER_HOUR,
                default=values.get(CONF_KG_PER_HOUR, DEFAULT_KG_PER_HOUR),
            )
        ] = _number(0.1, 50, 0.1, "kg/h")
    fields[
        vol.Required(
            CONF_MAX_STEP_KG, default=values.get(CONF_MAX_STEP_KG, DEFAULT_MAX_STEP_KG)
        )
    ] = _number(0.5, 500, 0.5, "kg")
    return vol.Schema(fields)


def _storage_schema(values: dict[str, Any]) -> vol.Schema:
    """Fields describing the storage."""
    level_default = values.get(CONF_LEVEL_ENTITY)
    level_key = (
        vol.Optional(CONF_LEVEL_ENTITY, default=level_default)
        if level_default
        else vol.Optional(CONF_LEVEL_ENTITY)
    )
    return vol.Schema(
        {
            vol.Required(
                CONF_CAPACITY_KG,
                default=values.get(CONF_CAPACITY_KG, DEFAULT_CAPACITY_KG),
            ): _number(10, 100000, 10, "kg"),
            vol.Required(
                CONF_MIN_STOCK_PERCENT,
                default=values.get(CONF_MIN_STOCK_PERCENT, DEFAULT_MIN_STOCK_PERCENT),
            ): _number(0, 90, 1, "%"),
            level_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
        }
    )


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    """Drop an empty optional fill level entity."""
    if not data.get(CONF_LEVEL_ENTITY):
        data.pop(CONF_LEVEL_ENTITY, None)
    return data


class PelletStockConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup assistant."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return PelletStockOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: name and where the consumption comes from."""
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            self._async_abort_entries_match({CONF_NAME: name})
            self._data = {
                CONF_NAME: name,
                CONF_SOURCE_TYPE: user_input[CONF_SOURCE_TYPE],
            }
            return await self.async_step_source()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=DEFAULT_NAME
                    ): selector.TextSelector(),
                    vol.Required(
                        CONF_SOURCE_TYPE, default=SOURCE_KG
                    ): _source_type_selector(),
                }
            ),
        )

    async def async_step_source(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: details of the consumption source."""
        source_type = self._data[CONF_SOURCE_TYPE]
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_storage()
        return self.async_show_form(
            step_id=f"source_{source_type}",
            data_schema=_source_schema(source_type, {}),
        )

    async def async_step_source_kg_counter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Form handler for the kg counter source."""
        return await self.async_step_source(user_input)

    async def async_step_source_energy_counter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Form handler for the energy source."""
        return await self.async_step_source(user_input)

    async def async_step_source_runtime(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Form handler for the burner runtime source."""
        return await self.async_step_source(user_input)

    async def async_step_storage(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: the storage itself."""
        if user_input is not None:
            self._data.update(_clean(user_input))
            return await self.async_step_start()
        return self.async_show_form(step_id="storage", data_schema=_storage_schema({}))

    async def async_step_start(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4: what is in the storage today."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

        history: dict[Any, Any] = {}
        if self._data[CONF_SOURCE_ENTITY].startswith("sensor."):
            # Only sensors have long-term statistics.
            history[vol.Required(CONF_IMPORT_HISTORY, default=True)] = (
                selector.BooleanSelector()
            )
        stock_default = 0.0
        if level_entity := self._data.get(CONF_LEVEL_ENTITY):
            stock_default = self._level_default(level_entity)
        return self.async_show_form(
            step_id="start",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INITIAL_STOCK_KG, default=stock_default): _number(
                        0, 100000, 1, "kg"
                    ),
                    vol.Required(
                        CONF_INITIAL_PRICE_PER_TONNE, default=DEFAULT_PRICE_PER_TONNE
                    ): _number(0, 5000, 0.01, f"{self.hass.config.currency}/t"),
                    **history,
                }
            ),
        )

    def _level_default(self, entity_id: str) -> float:
        """Suggest the current fill level in kg as start value."""
        state = self.hass.states.get(entity_id)
        if state is None:
            return 0.0
        try:
            value = float(state.state)
        except ValueError:
            return 0.0
        if state.attributes.get("unit_of_measurement") == "%":
            return round(self._data[CONF_CAPACITY_KG] * value / 100)
        if state.attributes.get("unit_of_measurement") == "t":
            return round(value * 1000)
        return round(value)


class PelletStockOptionsFlow(OptionsFlow):
    """Change the settings later. Stock and history are kept."""

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}

    @property
    def _current(self) -> dict[str, Any]:
        return {**self.config_entry.data, **self.config_entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the consumption source type."""
        if user_input is not None:
            self._data = dict(user_input)
            return await self.async_step_source()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SOURCE_TYPE, default=self._current[CONF_SOURCE_TYPE]
                    ): _source_type_selector(),
                }
            ),
        )

    async def async_step_source(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Details of the consumption source."""
        source_type = self._data[CONF_SOURCE_TYPE]
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_storage()
        values = self._current if source_type == self._current[CONF_SOURCE_TYPE] else {}
        return self.async_show_form(
            step_id=f"source_{source_type}",
            data_schema=_source_schema(source_type, values),
        )

    async def async_step_source_kg_counter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Form handler for the kg counter source."""
        return await self.async_step_source(user_input)

    async def async_step_source_energy_counter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Form handler for the energy source."""
        return await self.async_step_source(user_input)

    async def async_step_source_runtime(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Form handler for the burner runtime source."""
        return await self.async_step_source(user_input)

    async def async_step_storage(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Describe the storage."""
        if user_input is not None:
            self._data.update(user_input)
            if not user_input.get(CONF_LEVEL_ENTITY):
                self._data[CONF_LEVEL_ENTITY] = None
            return self.async_create_entry(data=self._data)
        return self.async_show_form(
            step_id="storage", data_schema=_storage_schema(self._current)
        )
