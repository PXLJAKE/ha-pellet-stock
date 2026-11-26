"""Pure calculation model for one pellet storage.

No Home Assistant imports here, so the logic is easy to test and to reason
about. The manager feeds consumption and deliveries in and reads values out.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
import uuid


@dataclass(slots=True)
class Delivery:
    """One pellet delivery."""

    id: str
    date: str  # ISO date
    kg: float
    price_total: float
    note: str = ""


@dataclass(slots=True)
class RangeEstimate:
    """Result of the range calculation, with the facts behind it."""

    days: float | None
    avg_kg_per_day: float | None
    basis: str  # "full_days", "partial_day", "no_data", "no_consumption", "empty"
    basis_days: float = 0.0


@dataclass(slots=True)
class CounterTracker:
    """Turn a counter sensor (total or daily resetting) into consumption steps.

    The baseline is a high-water mark: small backward jumps are ignored and
    do not cause double counting when the counter climbs back. A drop larger
    than the plausibility limit, or a drop to zero, is treated as a reset.
    So is a drop to a small value after the day changed: a daily counter
    whose zero at midnight was missed (e.g. 4.0 yesterday, 0.5 today).
    """

    baseline: float | None = None
    baseline_day: str | None = None  # local date the baseline was last raised or reset

    def step(  # noqa: PLR0911
        self, value: float, max_step: float, day: str | None = None
    ) -> tuple[float, str]:
        """Return (consumption since last value, decision)."""
        if self.baseline is None:
            self._set(value, day)
            return 0.0, "baseline"
        delta = value - self.baseline
        if delta > 0:
            self._set(value, day)
            if delta > max_step:
                return 0.0, "implausible_jump"
            return delta, "counted"
        if delta == 0:
            return 0.0, "unchanged"
        # The counter went down.
        new_day = (
            day is not None
            and self.baseline_day is not None
            and day != self.baseline_day
        )
        if value == 0 or -delta > max_step or (new_day and value <= max_step):
            self._set(value, day)
            if 0 < value <= max_step:
                return value, "reset_counted"
            return 0.0, "reset"
        return 0.0, "small_backstep"

    def _set(self, value: float, day: str | None) -> None:
        self.baseline = value
        if day is not None:
            self.baseline_day = day


@dataclass
class StockModel:
    """Stock, consumption and cost of one pellet storage."""

    stock_kg: float = 0.0
    avg_price_per_kg: float = 0.0
    total_consumed_kg: float = 0.0
    tracking_since: str = ""  # ISO datetime
    daily_kg: dict[str, float] = field(default_factory=dict)
    daily_cost: dict[str, float] = field(default_factory=dict)
    kg_by_month: dict[str, float] = field(default_factory=dict)  # kept forever (small)
    cost_by_month: dict[str, float] = field(default_factory=dict)
    cost_by_year: dict[str, float] = field(default_factory=dict)
    deliveries: list[Delivery] = field(default_factory=list)
    counter: CounterTracker = field(default_factory=CounterTracker)
    runtime_on_since: str | None = None  # ISO datetime while the burner runs
    source_key: str = ""  # identifies the source setup the counter baseline belongs to

    # ----- changes -----

    def consume(self, kg: float, when: datetime) -> None:
        """Book consumption at the given local time."""
        if kg <= 0:
            return
        day = when.date()
        self.stock_kg = max(0.0, self.stock_kg - kg)
        self.total_consumed_kg += kg
        key = day.isoformat()
        self.daily_kg[key] = self.daily_kg.get(key, 0.0) + kg
        cost = kg * self.avg_price_per_kg
        month = key[:7]
        year = key[:4]
        self.daily_cost[key] = self.daily_cost.get(key, 0.0) + cost
        self.kg_by_month[month] = self.kg_by_month.get(month, 0.0) + kg
        self.cost_by_month[month] = self.cost_by_month.get(month, 0.0) + cost
        self.cost_by_year[year] = self.cost_by_year.get(year, 0.0) + cost

    def add_delivery(
        self, kg: float, price_total: float, day: date, note: str = ""
    ) -> Delivery:
        """Add a delivery and update the moving average price."""
        if kg <= 0:
            raise ValueError("kg must be positive")
        if price_total < 0:
            raise ValueError("price must not be negative")
        value_before = self.stock_kg * self.avg_price_per_kg
        self.stock_kg += kg
        self.avg_price_per_kg = (value_before + price_total) / self.stock_kg
        delivery = Delivery(
            id=uuid.uuid4().hex,
            date=day.isoformat(),
            kg=kg,
            price_total=price_total,
            note=note,
        )
        self.deliveries.append(delivery)
        self.deliveries.sort(key=lambda d: d.date)
        return delivery

    def remove_delivery(self, delivery_id: str) -> Delivery | None:
        """Remove a wrongly entered delivery and take its kg and value back out.

        The average price is reversed by value. Pellets used since then cannot
        be told apart, so the result is a close approximation.
        """
        for delivery in self.deliveries:
            if delivery.id == delivery_id:
                break
        else:
            return None
        self.deliveries.remove(delivery)
        value = self.stock_kg * self.avg_price_per_kg - delivery.price_total
        self.stock_kg = max(0.0, self.stock_kg - delivery.kg)
        if self.stock_kg > 0:
            self.avg_price_per_kg = max(0.0, value) / self.stock_kg
        return delivery

    @property
    def last_delivery(self) -> Delivery | None:
        """Return the most recent delivery."""
        return self.deliveries[-1] if self.deliveries else None

    def set_stock(self, kg: float) -> float:
        """Correct the stock (e.g. from a scale). Returns the difference."""
        kg = max(0.0, kg)
        diff = kg - self.stock_kg
        self.stock_kg = kg
        return diff

    def prune(self, today: date, keep_days: int) -> None:
        """Drop daily values older than keep_days."""
        cutoff = (today - timedelta(days=keep_days)).isoformat()
        self.daily_kg = {k: v for k, v in self.daily_kg.items() if k >= cutoff}
        self.daily_cost = {k: v for k, v in self.daily_cost.items() if k >= cutoff}

    # ----- values -----

    def consumed_on(self, day: date) -> float:
        """Return consumption of one day."""
        return self.daily_kg.get(day.isoformat(), 0.0)

    def estimate_range(self, now: datetime, window_days: int) -> RangeEstimate:
        """Estimate average consumption and days until the storage is empty.

        Uses the last full days (up to window_days) since tracking started.
        Days without consumption count as zero, because a warm week is real.
        Before the first full day, today's consumption is extrapolated once
        at least six hours of data exist.
        """
        if self.stock_kg <= 0:
            return RangeEstimate(0.0, None, "empty")
        today = now.date()
        start = (
            datetime.fromisoformat(self.tracking_since) if self.tracking_since else now
        )
        first_full_day = start.date() + timedelta(days=1)
        if start.time() == datetime.min.time():
            first_full_day = start.date()
        full_days = (today - first_full_day).days
        n = min(window_days, full_days)
        if n >= 1:
            total = sum(
                self.consumed_on(today - timedelta(days=i)) for i in range(1, n + 1)
            )
            avg = total / n
            basis = "full_days"
            basis_days = float(n)
        else:
            hours = (now - start).total_seconds() / 3600
            if hours < 6:
                return RangeEstimate(None, None, "no_data", hours / 24)
            avg = self.consumed_on(today) / hours * 24
            basis = "partial_day"
            basis_days = hours / 24
        if avg <= 0:
            return RangeEstimate(None, 0.0, "no_consumption", basis_days)
        return RangeEstimate(self.stock_kg / avg, avg, basis, basis_days)

    # ----- persistence -----

    def to_dict(self) -> dict[str, Any]:
        """Serialize for the HA store."""
        data = asdict(self)
        data["counter"] = {
            "baseline": self.counter.baseline,
            "baseline_day": self.counter.baseline_day,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StockModel:
        """Restore from the HA store."""
        model = cls._from_dict(data)
        if "kg_by_month" not in data:
            # Data from before monthly totals existed: rebuild from the days.
            for day, kg in model.daily_kg.items():
                model.kg_by_month[day[:7]] = model.kg_by_month.get(day[:7], 0.0) + kg
        return model

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> StockModel:
        return cls(
            stock_kg=float(data.get("stock_kg", 0.0)),
            avg_price_per_kg=float(data.get("avg_price_per_kg", 0.0)),
            total_consumed_kg=float(data.get("total_consumed_kg", 0.0)),
            tracking_since=data.get("tracking_since", ""),
            daily_kg=dict(data.get("daily_kg", {})),
            daily_cost=dict(data.get("daily_cost", {})),
            kg_by_month=dict(data.get("kg_by_month", {})),
            cost_by_month=dict(data.get("cost_by_month", {})),
            cost_by_year=dict(data.get("cost_by_year", {})),
            deliveries=[Delivery(**d) for d in data.get("deliveries", [])],
            counter=CounterTracker(
                baseline=data.get("counter", {}).get("baseline"),
                baseline_day=data.get("counter", {}).get("baseline_day"),
            ),
            runtime_on_since=data.get("runtime_on_since"),
            source_key=data.get("source_key", ""),
        )

    # ----- analysis -----

    def months(self) -> list[dict[str, Any]]:
        """Return all months with consumption and cost, oldest first."""
        keys = sorted(set(self.kg_by_month) | set(self.cost_by_month))
        return [
            {
                "period": k,
                "kg": round(self.kg_by_month.get(k, 0.0), 2),
                "cost": round(self.cost_by_month.get(k, 0.0), 2),
            }
            for k in keys
        ]

    def years(self) -> list[dict[str, Any]]:
        """Return all years with consumption and cost, oldest first."""
        totals: dict[str, list[float]] = {}
        for m in self.months():
            t = totals.setdefault(m["period"][:4], [0.0, 0.0])
            t[0] += m["kg"]
            t[1] += m["cost"]
        return [
            {"period": y, "kg": round(kg, 2), "cost": round(cost, 2)}
            for y, (kg, cost) in sorted(totals.items())
        ]

    def days_of_month(self, month: str) -> list[dict[str, Any]]:
        """Return the stored days of one month ("YYYY-MM")."""
        return [
            {
                "period": k,
                "kg": round(v, 2),
                "cost": round(self.daily_cost.get(k, 0.0), 2),
            }
            for k, v in sorted(self.daily_kg.items())
            if k.startswith(month)
        ]

    def weeks(self, today: date, count: int) -> list[dict[str, Any]]:
        """Return the last `count` ISO weeks (Monday to Sunday), oldest first."""
        monday = today - timedelta(days=today.weekday())
        result = []
        for i in range(count - 1, -1, -1):
            start = monday - timedelta(weeks=i)
            days = [(start + timedelta(days=d)).isoformat() for d in range(7)]
            iso = start.isocalendar()
            result.append(
                {
                    "period": f"{iso.year}-W{iso.week:02d}",
                    "start": start.isoformat(),
                    "kg": round(sum(self.daily_kg.get(d, 0.0) for d in days), 2),
                    "cost": round(sum(self.daily_cost.get(d, 0.0) for d in days), 2),
                    "days": [
                        {
                            "period": d,
                            "kg": round(self.daily_kg.get(d, 0.0), 2),
                            "cost": round(self.daily_cost.get(d, 0.0), 2),
                        }
                        for d in days
                    ],
                }
            )
        return result
