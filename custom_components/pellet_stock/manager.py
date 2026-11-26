"""Glue between Home Assistant and the calculation model.

Event driven: listens to state changes of the configured sensors and to the
day change at midnight. Nothing is polled. Data is written to disk with a
delay so frequent sensor updates do not wear out SD cards.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfTime,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import explain
from .const import (
    AVERAGE_DAYS,
    CONF_CALORIFIC_VALUE,
    CONF_CAPACITY_KG,
    CONF_EFFICIENCY,
    CONF_INITIAL_PRICE_PER_TONNE,
    CONF_INITIAL_STOCK_KG,
    CONF_KG_PER_HOUR,
    CONF_LEVEL_ENTITY,
    CONF_MAX_STEP_KG,
    CONF_MIN_STOCK_PERCENT,
    CONF_SOURCE_ENTITY,
    CONF_SOURCE_TYPE,
    DEFAULT_CALORIFIC_VALUE,
    DEFAULT_EFFICIENCY,
    DEFAULT_KG_PER_HOUR,
    DEFAULT_MAX_STEP_KG,
    DEFAULT_MIN_STOCK_PERCENT,
    DOMAIN,
    EVENT_LOW_STOCK,
    HISTORY_DAYS,
    SAVE_DELAY_SECONDS,
    SOURCE_ENERGY,
    SOURCE_RUNTIME,
    STORAGE_VERSION,
)
from .model import Delivery, RangeEstimate, StockModel

_LOGGER = logging.getLogger(__name__)

_ENERGY_TO_KWH = {
    UnitOfEnergy.WATT_HOUR: 0.001,
    UnitOfEnergy.KILO_WATT_HOUR: 1.0,
    UnitOfEnergy.MEGA_WATT_HOUR: 1000.0,
}
_TIME_TO_HOURS = {
    UnitOfTime.SECONDS: 1 / 3600,
    UnitOfTime.MINUTES: 1 / 60,
    UnitOfTime.HOURS: 1.0,
    UnitOfTime.DAYS: 24.0,
}
_MASS_TO_KG = {
    UnitOfMass.GRAMS: 0.001,
    UnitOfMass.KILOGRAMS: 1.0,
    "t": 1000.0,
}


@dataclass(slots=True)
class SourceDecision:
    """Last automatic decision about the consumption sensor ("Why?")."""

    reason: str
    at: datetime


class PelletStockManager:
    """Owns the model of one storage and keeps it in sync with HA."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.config: dict[str, Any] = {**entry.data, **entry.options}
        self.lang = explain.language(hass.config.language)
        self.model = StockModel()
        self.last_decision: SourceDecision | None = None
        self.low_stock: bool = False
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []

    # ----- configuration helpers -----

    @property
    def source_type(self) -> str:
        """Return the configured consumption source type."""
        return self.config[CONF_SOURCE_TYPE]

    @property
    def calorific_value(self) -> float:
        """Return kWh per kg."""
        return float(self.config.get(CONF_CALORIFIC_VALUE, DEFAULT_CALORIFIC_VALUE))

    @property
    def capacity_kg(self) -> float:
        """Return the storage capacity in kg."""
        return float(self.config[CONF_CAPACITY_KG])

    @property
    def min_stock_kg(self) -> float:
        """Return the minimum stock in kg."""
        percent = float(
            self.config.get(CONF_MIN_STOCK_PERCENT, DEFAULT_MIN_STOCK_PERCENT)
        )
        return self.capacity_kg * percent / 100

    @property
    def max_step_kg(self) -> float:
        """Return the plausibility limit for one sensor step."""
        return float(self.config.get(CONF_MAX_STEP_KG, DEFAULT_MAX_STEP_KG))

    @property
    def level_entity(self) -> str | None:
        """Return the optional fill level / scale entity."""
        return self.config.get(CONF_LEVEL_ENTITY) or None

    # ----- lifecycle -----

    async def async_load(self) -> None:
        """Load stored data or start fresh from the setup values."""
        data = await self._store.async_load()
        if data is not None:
            self.model = StockModel.from_dict(data)
        else:
            now = dt_util.now()
            price_per_t = float(self.config.get(CONF_INITIAL_PRICE_PER_TONNE, 0.0))
            self.model = StockModel(
                stock_kg=float(self.config.get(CONF_INITIAL_STOCK_KG, 0.0)),
                avg_price_per_kg=price_per_t / 1000,
                tracking_since=now.isoformat(),
            )
            await self._store.async_save(self.model.to_dict())
        key = self._source_key()
        if self.model.source_key != key:
            # The source or its conversion changed: start counting from the
            # next value instead of booking the difference as consumption.
            self.model.counter.baseline = None
            self.model.runtime_on_since = None
            self.model.source_key = key
        self.low_stock = self.model.stock_kg < self.min_stock_kg

    def _source_key(self) -> str:
        parts = [
            self.config.get(CONF_SOURCE_TYPE),
            self.config.get(CONF_SOURCE_ENTITY),
            self.config.get(CONF_CALORIFIC_VALUE),
            self.config.get(CONF_EFFICIENCY),
            self.config.get(CONF_KG_PER_HOUR),
        ]
        return "|".join(str(p) for p in parts)

    @callback
    def async_start(self) -> None:
        """Subscribe to sensor changes and the day change."""
        source = self.config[CONF_SOURCE_ENTITY]
        self._unsubs.append(
            async_track_state_change_event(self.hass, [source], self._on_source_event)
        )
        if self.level_entity:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [self.level_entity], self._on_level_event
                )
            )
        self._unsubs.append(
            async_track_time_change(
                self.hass, self._on_midnight, hour=0, minute=0, second=10
            )
        )
        state = self.hass.states.get(source)
        if self.source_type == SOURCE_RUNTIME and self.model.runtime_on_since:
            # A burner run that was open before the restart: the time while
            # Home Assistant was down is unknown, so it is not counted.
            self.model.runtime_on_since = None
            if state is None or state.state != STATE_ON:
                self._decide("source_burner_restart", dt_util.now())
        # Take the current value as baseline (or continue from the stored one).
        if state is not None:
            self._handle_source_state(state, None)

    async def async_stop(self) -> None:
        """Unsubscribe and write pending data."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._store.async_save(self.model.to_dict())

    async def async_remove_store(self) -> None:
        """Delete stored data when the entry is removed."""
        await self._store.async_remove()

    # ----- listeners -----

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> CALLBACK_TYPE:
        """Register an entity update callback."""
        self._listeners.append(update)

        @callback
        def remove() -> None:
            self._listeners.remove(update)

        return remove

    @callback
    def _changed(self, save: bool = True) -> None:
        if save:
            self._store.async_delay_save(self.model.to_dict, SAVE_DELAY_SECONDS)
        self._check_low_stock()
        for update in list(self._listeners):
            update()

    @callback
    def _check_low_stock(self) -> None:
        below = self.model.stock_kg < self.min_stock_kg
        if below and not self.low_stock:
            self.hass.bus.async_fire(
                EVENT_LOW_STOCK,
                {
                    "entry_id": self.entry.entry_id,
                    "name": self.entry.title,
                    "stock_kg": round(self.model.stock_kg, 1),
                    "min_stock_kg": round(self.min_stock_kg, 1),
                    "reason": self.low_stock_reason(),
                },
            )
        self.low_stock = below

    # ----- source handling -----

    @callback
    def _on_source_event(self, event: Event[EventStateChangedData]) -> None:
        if (new := event.data["new_state"]) is None:
            return
        self._handle_source_state(new, event.data["old_state"])

    @callback
    def _handle_source_state(self, new: State, old: State | None) -> None:
        now = dt_util.now()
        if new.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._decide("source_unavailable", now)
            self._changed(save=False)
            return

        if self.source_type == SOURCE_RUNTIME and new.domain != "sensor":
            self._handle_burner(new, now)
            return

        value = self._counter_value_in_kg(new)
        if value is None:
            self._decide("source_unavailable", now)
            self._changed(save=False)
            return

        before = self.model.counter.baseline
        kg, decision = self.model.counter.step(
            value, self.max_step_kg, now.date().isoformat()
        )
        self.model.consume(kg, now)
        self._decide(
            f"source_{decision}",
            now,
            kg=kg,
            value=value,
            jump=value - (before or 0.0),
            max=self.max_step_kg,
        )
        self._changed(save=decision != "unchanged")

    @callback
    def _handle_burner(self, new: State, now: datetime) -> None:
        kg_per_hour = float(self.config.get(CONF_KG_PER_HOUR, DEFAULT_KG_PER_HOUR))
        if new.state == STATE_ON:
            if self.model.runtime_on_since is None:
                self.model.runtime_on_since = now.isoformat()
            self._decide("source_burner_on", now)
            self._changed()
            return
        if self.model.runtime_on_since is None:
            self._changed(save=False)
            return
        started = datetime.fromisoformat(self.model.runtime_on_since)
        self.model.runtime_on_since = None
        hours = max(0.0, (now - started).total_seconds() / 3600)
        kg = hours * kg_per_hour
        self.model.consume(kg, now)
        self._decide("source_burner_off", now, hours=hours, kg=kg)
        self._changed()

    def _counter_value_in_kg(self, state: State) -> float | None:
        """Convert a counter sensor state into kg of pellets."""
        try:
            value = float(state.state)
        except ValueError:
            return None
        unit = state.attributes.get("unit_of_measurement")
        if self.source_type == SOURCE_ENERGY:
            kwh = value * _ENERGY_TO_KWH.get(unit, 1.0)
            efficiency = float(self.config.get(CONF_EFFICIENCY, DEFAULT_EFFICIENCY))
            return kwh / (efficiency / 100) / self.calorific_value
        if self.source_type == SOURCE_RUNTIME:
            hours = value * _TIME_TO_HOURS.get(unit, 1.0)
            return hours * float(self.config.get(CONF_KG_PER_HOUR, DEFAULT_KG_PER_HOUR))
        return value * _MASS_TO_KG.get(unit, 1.0)

    def _decide(self, key: str, now: datetime, **values: float) -> None:
        self.last_decision = SourceDecision(explain.text(self.lang, key, **values), now)

    # ----- fill level -----

    @callback
    def _on_level_event(self, event: Event[EventStateChangedData]) -> None:
        self._changed(save=False)

    def level_kg(self) -> float | None:
        """Return the fill level sensor value in kg, if available."""
        if not self.level_entity:
            return None
        state = self.hass.states.get(self.level_entity)
        if state is None:
            return None
        try:
            value = float(state.state)
        except ValueError:
            return None
        unit = state.attributes.get("unit_of_measurement")
        if unit == PERCENTAGE:
            return self.capacity_kg * value / 100
        return value * _MASS_TO_KG.get(unit, 1.0)

    def level_deviation_kg(self) -> float | None:
        """Return calculated stock minus measured level."""
        level = self.level_kg()
        return None if level is None else self.model.stock_kg - level

    @callback
    def async_adopt_level(self) -> bool:
        """Take the fill level sensor value as the new stock."""
        level = self.level_kg()
        if level is None:
            return False
        self.model.set_stock(level)
        self._changed()
        return True

    # ----- deliveries and corrections -----

    async def async_add_delivery(
        self, kg: float, price_total: float, day: date, note: str = ""
    ) -> Delivery:
        """Add a delivery and save right away (deliveries are rare and important)."""
        delivery = self.model.add_delivery(kg, price_total, day, note)
        self._changed(save=False)
        await self._store.async_save(self.model.to_dict())
        return delivery

    async def async_delete_delivery(self, delivery_id: str) -> Delivery | None:
        """Remove a wrongly entered delivery."""
        delivery = self.model.remove_delivery(delivery_id)
        if delivery is not None:
            self._changed(save=False)
            await self._store.async_save(self.model.to_dict())
        return delivery

    async def async_correct_stock(self, kg: float) -> float:
        """Set the stock to a known value, e.g. after measuring."""
        diff = self.model.set_stock(kg)
        self._changed(save=False)
        await self._store.async_save(self.model.to_dict())
        return diff

    # ----- midnight -----

    @callback
    def _on_midnight(self, now: datetime) -> None:
        self.model.prune(now.date(), HISTORY_DAYS)
        self._changed()

    # ----- analysis for the dashboard card -----

    def export(self, month: str | None = None) -> dict[str, Any]:
        """Return everything the card and its popup show, in one answer.

        Sent over the WebSocket API on demand, so the history never has to be
        stored as state attributes in the recorder database.
        """
        now = dt_util.now()
        est = self.estimate()
        model = self.model
        data: dict[str, Any] = {
            "name": self.entry.title,
            "entry_id": self.entry.entry_id,
            "currency": self.hass.config.currency,
            "calorific_value": self.calorific_value,
            "kpis": {
                "stock_kg": round(model.stock_kg, 1),
                "capacity_kg": self.capacity_kg,
                "min_stock_kg": round(self.min_stock_kg, 1),
                "low_stock": self.low_stock,
                "range_days": None if est.days is None else round(est.days, 1),
                "range_reason": self.range_reason(),
                "avg_kg_per_day": None
                if est.avg_kg_per_day is None
                else round(est.avg_kg_per_day, 2),
                "today_kg": round(model.consumed_on(now.date()), 2),
                "month_kg": round(model.kg_by_month.get(now.strftime("%Y-%m"), 0.0), 2),
                "month_cost": round(self.cost_this_month(), 2),
                "year_cost": round(self.cost_this_year(), 2),
                "total_kg": round(model.total_consumed_kg, 1),
                "price_per_tonne": round(model.avg_price_per_kg * 1000, 2)
                if model.avg_price_per_kg > 0
                else None,
                "price_per_kwh": None
                if (p := self.price_per_kwh()) is None
                else round(p, 5),
                "tracking_since": model.tracking_since,
            },
            "months": model.months(),
            "years": model.years(),
            "weeks": model.weeks(now.date(), 26),
            "deliveries": [
                {
                    "id": d.id,
                    "date": d.date,
                    "kg": d.kg,
                    "price": d.price_total,
                    "note": d.note,
                }
                for d in reversed(model.deliveries)
            ],
        }
        if month:
            data["days"] = model.days_of_month(month)
        return data

    # ----- derived values -----

    def estimate(self) -> RangeEstimate:
        """Return the current range estimate."""
        return self.model.estimate_range(dt_util.now(), AVERAGE_DAYS)

    def range_reason(self) -> str:
        """Explain the range."""
        return explain.range_reason(self.lang, self.estimate(), self.model.stock_kg)

    def low_stock_reason(self) -> str:
        """Explain the low stock state."""
        percent = float(
            self.config.get(CONF_MIN_STOCK_PERCENT, DEFAULT_MIN_STOCK_PERCENT)
        )
        below = self.model.stock_kg < self.min_stock_kg
        key = "low_stock_yes" if below else "low_stock_no"
        return explain.text(
            self.lang,
            key,
            stock=self.model.stock_kg,
            min=self.min_stock_kg,
            percent=percent,
            capacity=self.capacity_kg,
        )

    def price_per_kwh(self) -> float | None:
        """Return the average pellet price per kWh of fuel energy."""
        if self.model.avg_price_per_kg <= 0:
            return None
        return self.model.avg_price_per_kg / self.calorific_value

    def cost_this_month(self) -> float:
        """Return the cost of pellets used this month."""
        return self.model.cost_by_month.get(dt_util.now().strftime("%Y-%m"), 0.0)

    def cost_this_year(self) -> float:
        """Return the cost of pellets used this year."""
        return self.model.cost_by_year.get(dt_util.now().strftime("%Y"), 0.0)
