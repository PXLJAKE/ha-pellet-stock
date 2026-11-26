"""Shared fixtures."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pellet_stock.const import DOMAIN

BASE_DATA: dict[str, Any] = {
    "name": "Pelletsilo",
    "source_type": "kg_counter",
    "source_entity": "sensor.boiler_usage_today",
    "calorific_value": 4.8,
    "max_step_kg": 10.0,
    "capacity_kg": 6000,
    "min_stock_percent": 10,
    "initial_stock_kg": 5000,
    "initial_price_per_tonne": 400.0,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom integrations in all tests."""
    return


@pytest.fixture
def entry_data() -> dict[str, Any]:
    """Return config entry data for a silo with a kg counter."""
    return dict(BASE_DATA)


@pytest.fixture
def mock_entry(entry_data) -> MockConfigEntry:
    """Return a config entry for a pellet silo."""
    return MockConfigEntry(domain=DOMAIN, title="Pelletsilo", data=entry_data)
