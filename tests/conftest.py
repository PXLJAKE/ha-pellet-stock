"""Shared fixtures."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pellet_stock.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom integrations in all tests."""
    return


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Return a config entry for a pellet silo."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Pelletsilo",
        data={"name": "Pelletsilo"},
    )
