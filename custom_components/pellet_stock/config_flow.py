"""Config flow for Pellet Stock Manager.

This is the scaffold version: it only asks for a name. The full assistant
(consumption source, capacity, minimum stock, fill level sensor) follows in
the MVP pull requests.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DEFAULT_NAME, DOMAIN


class PelletStockConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup assistant."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step: name the storage."""
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            self._async_abort_entries_match({CONF_NAME: name})
            return self.async_create_entry(title=name, data={CONF_NAME: name})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=DEFAULT_NAME
                    ): selector.TextSelector(),
                }
            ),
        )
