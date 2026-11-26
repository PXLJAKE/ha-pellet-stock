"""Serve the dashboard card from the integration (no manual resource needed)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_FILE = "pellet-stock-card.js"
URL_BASE = "/pellet_stock_static"
_FRONTEND_MODULES = "frontend_extra_module_url"


def _version() -> str:
    manifest = Path(__file__).parent.parent / "manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["version"]


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card file and load it on every dashboard."""
    if hass.http is None:
        return
    version = await hass.async_add_executor_job(_version)
    path = Path(__file__).parent / CARD_FILE
    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"{URL_BASE}/{CARD_FILE}", str(path), cache_headers=True)]
    )
    if _FRONTEND_MODULES not in hass.data:
        _LOGGER.debug("Frontend not loaded, card is served but not auto-loaded")
        return
    # Version in the URL so browsers fetch the new card after an update.
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

    add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILE}?v={version}")
