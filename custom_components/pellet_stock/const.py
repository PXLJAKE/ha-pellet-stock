"""Constants for Pellet Stock Manager."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "pellet_stock"

DEFAULT_NAME: Final = "Pellet storage"

# Config keys
CONF_SOURCE_TYPE: Final = "source_type"
CONF_SOURCE_ENTITY: Final = "source_entity"
CONF_CALORIFIC_VALUE: Final = "calorific_value"
CONF_EFFICIENCY: Final = "efficiency"
CONF_KG_PER_HOUR: Final = "kg_per_hour"
CONF_MAX_STEP_KG: Final = "max_step_kg"
CONF_CAPACITY_KG: Final = "capacity_kg"
CONF_MIN_STOCK_PERCENT: Final = "min_stock_percent"
CONF_LEVEL_ENTITY: Final = "level_entity"
CONF_INITIAL_STOCK_KG: Final = "initial_stock_kg"
CONF_INITIAL_PRICE_PER_TONNE: Final = "initial_price_per_tonne"
CONF_IMPORT_HISTORY: Final = "import_history"

# Consumption source types
SOURCE_KG: Final = "kg_counter"
SOURCE_ENERGY: Final = "energy_counter"
SOURCE_RUNTIME: Final = "runtime"
SOURCE_TYPES: Final = [SOURCE_KG, SOURCE_ENERGY, SOURCE_RUNTIME]

# Defaults (explained in the setup assistant)
DEFAULT_CALORIFIC_VALUE: Final = 4.8  # kWh per kg, typical for ENplus A1 pellets
DEFAULT_EFFICIENCY: Final = 100  # percent; 100 = sensor already measures fuel energy
DEFAULT_KG_PER_HOUR: Final = 2.0
DEFAULT_MAX_STEP_KG: Final = 10.0
DEFAULT_CAPACITY_KG: Final = 5000
DEFAULT_MIN_STOCK_PERCENT: Final = 10
DEFAULT_PRICE_PER_TONNE: Final = 0.0

# Range calculation
AVERAGE_DAYS: Final = 14
MIN_DAYS_FOR_AVERAGE: Final = 1
HISTORY_DAYS: Final = 400

# Storage
STORAGE_VERSION: Final = 1
SAVE_DELAY_SECONDS: Final = 900  # write at most every 15 minutes (SD card friendly)

EVENT_LOW_STOCK: Final = f"{DOMAIN}_low_stock"
