"""Tests for the pure calculation model."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from custom_components.pellet_stock.model import CounterTracker, StockModel


def test_counter_daily_reset_like_oekofen() -> None:
    """A daily counter that climbs, glitches and resets at midnight."""
    c = CounterTracker()
    steps = [
        (10, (0.0, "baseline")),
        (12, (2.0, "counted")),
        (11, (0.0, "small_backstep")),  # glitch down
        (12, (0.0, "unchanged")),  # back up: no double count
        (13, (1.0, "counted")),
        (40, (0.0, "implausible_jump")),  # spike above limit
        (41, (1.0, "counted")),
        (0, (0.0, "reset")),  # midnight
        (2, (2.0, "counted")),
    ]
    for value, expected in steps:
        assert c.step(value, 10) == expected


def test_counter_reset_with_value_counts_since_reset() -> None:
    """When the first value after a reset is already above zero, count it."""
    c = CounterTracker(baseline=29)
    assert c.step(1.5, 10) == (1.5, "reset_counted")


def test_consume_books_cost_and_never_goes_negative() -> None:
    """Consumption lowers stock, adds cost and stops at zero."""
    m = StockModel(stock_kg=5, avg_price_per_kg=0.4)
    m.consume(3, datetime(2026, 11, 26, 10))
    assert m.stock_kg == 2
    assert m.total_consumed_kg == 3
    assert m.daily_kg == {"2026-11-26": 3}
    assert m.cost_by_month["2026-11"] == pytest.approx(1.2)
    assert m.cost_by_year["2026"] == pytest.approx(1.2)
    m.consume(10, datetime(2026, 11, 26, 11))
    assert m.stock_kg == 0
    m.consume(-1, datetime(2026, 11, 26, 12))
    assert m.total_consumed_kg == 13


def test_delivery_moving_average_price() -> None:
    """The average price mixes old stock and the new delivery by weight."""
    m = StockModel(stock_kg=1000, avg_price_per_kg=0.30)
    m.add_delivery(3000, 1200.0, date(2026, 11, 1))
    assert m.stock_kg == 4000
    assert m.avg_price_per_kg == pytest.approx((300 + 1200) / 4000)
    assert len(m.deliveries) == 1
    with pytest.raises(ValueError):
        m.add_delivery(0, 10, date(2026, 11, 1))
    with pytest.raises(ValueError):
        m.add_delivery(10, -1, date(2026, 11, 1))


def test_set_stock_returns_difference() -> None:
    """Correcting the stock reports the difference."""
    m = StockModel(stock_kg=500)
    assert m.set_stock(450) == -50
    assert m.set_stock(-5) == 0 - 450
    assert m.stock_kg == 0


def test_range_from_full_days() -> None:
    """Average of the last full days, zero days included."""
    start = datetime(2026, 11, 1, 15, 0)
    m = StockModel(stock_kg=1000, tracking_since=start.isoformat())
    for i, kg in enumerate([20, 0, 30], start=2):
        m.consume(kg, datetime(2026, 11, i, 12))
    now = datetime(2026, 11, 5, 8)
    est = m.estimate_range(now, 14)
    # Nov 1 is partial and excluded; Nov 2-4 are full days: 50 kg / 3 days.
    assert est.basis == "full_days"
    assert est.basis_days == 3
    assert est.avg_kg_per_day == pytest.approx(50 / 3)
    assert est.days == pytest.approx(950 / (50 / 3))


def test_range_window_is_limited() -> None:
    """Only the last window_days full days count."""
    start = datetime(2026, 10, 1, 0, 0)
    m = StockModel(stock_kg=100000, tracking_since=start.isoformat())
    for i in range(40):
        day = start + timedelta(days=i)
        m.consume(100 if i < 26 else 10, day.replace(hour=12))
    est = m.estimate_range(datetime(2026, 11, 10, 9), 14)
    assert est.avg_kg_per_day == pytest.approx(10)


def test_range_partial_day_and_no_data() -> None:
    """Before the first full day the range is extrapolated after 6 hours."""
    start = datetime(2026, 11, 26, 8, 0)
    m = StockModel(stock_kg=1000, tracking_since=start.isoformat())
    assert m.estimate_range(start + timedelta(hours=2), 14).basis == "no_data"
    m.consume(6, start + timedelta(hours=5))
    est = m.estimate_range(start + timedelta(hours=8), 14)
    assert est.basis == "partial_day"
    assert est.avg_kg_per_day == pytest.approx(18)


def test_range_no_consumption_and_empty() -> None:
    """Summer without use gives no range; empty storage gives 0."""
    start = datetime(2026, 7, 1, 0, 0)
    m = StockModel(stock_kg=1000, tracking_since=start.isoformat())
    est = m.estimate_range(datetime(2026, 7, 10, 9), 14)
    assert est.basis == "no_consumption"
    assert est.days is None
    m.stock_kg = 0
    assert m.estimate_range(datetime(2026, 7, 10, 9), 14).days == 0


def test_roundtrip_and_prune() -> None:
    """Data survives serialization; old days are dropped."""
    m = StockModel(stock_kg=100, tracking_since="2026-01-01T00:00:00")
    m.consume(1, datetime(2025, 1, 1, 12))
    m.consume(2, datetime(2026, 11, 1, 12))
    m.add_delivery(50, 20, date(2026, 11, 2), note="x")
    m.counter.baseline = 7.5
    restored = StockModel.from_dict(m.to_dict())
    assert restored == m
    restored.prune(date(2026, 11, 26), 400)
    assert list(restored.daily_kg) == ["2026-11-01"]


def test_remove_delivery() -> None:
    """Removing a delivery reverses stock and value; unknown IDs are ignored."""
    m = StockModel(stock_kg=1000, avg_price_per_kg=0.30)
    d = m.add_delivery(1000, 500, date(2026, 11, 1))
    assert m.last_delivery == d
    assert m.remove_delivery("missing") is None
    assert m.remove_delivery(d.id) == d
    assert m.stock_kg == 1000
    assert m.avg_price_per_kg == pytest.approx(0.30)
    assert m.last_delivery is None


def test_analysis_months_years_days_weeks() -> None:
    """Months, years, days of a month and weeks add up the booked consumption."""
    m = StockModel(stock_kg=1000, avg_price_per_kg=0.5)
    m.consume(10, datetime(2025, 12, 31, 12))
    m.consume(4, datetime(2026, 1, 1, 8))
    m.consume(6, datetime(2026, 1, 2, 8))
    assert m.months() == [
        {"period": "2025-12", "kg": 10.0, "cost": 5.0},
        {"period": "2026-01", "kg": 10.0, "cost": 5.0},
    ]
    assert m.years() == [
        {"period": "2025", "kg": 10.0, "cost": 5.0},
        {"period": "2026", "kg": 10.0, "cost": 5.0},
    ]
    assert [d["period"] for d in m.days_of_month("2026-01")] == [
        "2026-01-01",
        "2026-01-02",
    ]
    weeks = m.weeks(date(2026, 1, 2), 2)
    assert [w["period"] for w in weeks] == ["2025-W52", "2026-W01"]
    # Week 1 of 2026 runs from Monday 29 Dec 2025 to Sunday 4 Jan 2026.
    assert weeks[1]["start"] == "2025-12-29"
    assert weeks[1]["kg"] == 20.0
    assert len(weeks[1]["days"]) == 7
    assert weeks[1]["days"][2] == {"period": "2025-12-31", "kg": 10.0, "cost": 5.0}
