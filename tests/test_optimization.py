"""Tests for battery dispatch optimization."""

from datetime import datetime, timedelta

import pytest

from battery_arbitrage.domain import (
    BatteryConfig,
    MarketIntervals,
    OptimizationResult,
    Timeline,
    TimelinePrices,
)
from battery_arbitrage.optimization import optimize_battery

START_TIME = datetime(2024, 1, 1)
HALF_HOUR = timedelta(minutes=30)
ONE_HOUR = timedelta(hours=1)


def _timeline(
    prices: dict[str, tuple[float, ...]],
    market_intervals: MarketIntervals,
) -> Timeline:
    """Build a synthetic timeline with prices at each common half-hour step."""
    horizon = len(next(iter(prices.values())))
    timestamps = [
        START_TIME + step * HALF_HOUR for step in range(horizon)
    ]
    timeline_prices: TimelinePrices = {
        timestamp: {
            market_name: market_prices[step]
            for market_name, market_prices in prices.items()
        }
        for step, timestamp in enumerate(timestamps)
    }
    return Timeline(
        prices=timeline_prices,
        common_period=HALF_HOUR,
        market_intervals=dict(market_intervals),
    )


def _assert_dense_results(result: OptimizationResult) -> None:
    expected_power_keys = {
        (market_name, timestamp)
        for market_name in result.market_names
        for timestamp in result.timestamps
    }
    assert set(result.charge_mw) == expected_power_keys
    assert set(result.discharge_mw) == expected_power_keys
    assert set(result.energy_mwh) == set(result.timestamps)


def test_optimizes_basic_arbitrage() -> None:
    timeline = _timeline(
        {"Market 1": (10.0, 100.0)},
        {"Market 1": HALF_HOUR},
    )
    config = BatteryConfig(
        max_charge_mw=5.0,
        max_discharge_mw=5.0,
        storage_capacity_mwh=10.0,
        initial_energy_mwh=0.0,
    )

    result = optimize_battery(timeline, config)

    assert result.timestamps == (START_TIME, START_TIME + HALF_HOUR)
    assert result.market_names == ("Market 1",)
    assert result.timestep == HALF_HOUR
    _assert_dense_results(result)

    assert result.charge_mw[("Market 1", START_TIME)] == pytest.approx(5.0)
    assert result.discharge_mw[("Market 1", START_TIME)] == pytest.approx(0.0)
    assert result.charge_mw[
        ("Market 1", START_TIME + HALF_HOUR)
    ] == pytest.approx(0.0)
    assert result.discharge_mw[
        ("Market 1", START_TIME + HALF_HOUR)
    ] == pytest.approx(5.0)

    assert result.energy_mwh[START_TIME] == pytest.approx(0.0)
    assert result.energy_mwh[START_TIME + HALF_HOUR] == pytest.approx(2.5)
    assert result.total_profit_gbp == pytest.approx(225.0)


def test_respects_custom_power_limits() -> None:
    timeline = _timeline(
        {"Market 1": (10.0, 100.0)},
        {"Market 1": HALF_HOUR},
    )
    config = BatteryConfig(
        max_charge_mw=4.0,
        max_discharge_mw=4.0,
        storage_capacity_mwh=10.0,
        initial_energy_mwh=0.0,
    )

    result = optimize_battery(timeline, config)

    _assert_dense_results(result)
    assert result.charge_mw[("Market 1", START_TIME)] == pytest.approx(4.0)
    assert result.discharge_mw[
        ("Market 1", START_TIME + HALF_HOUR)
    ] == pytest.approx(4.0)
    assert result.energy_mwh[START_TIME] == pytest.approx(0.0)
    assert result.energy_mwh[
        START_TIME + HALF_HOUR
    ] == pytest.approx(2.0)
    assert result.total_profit_gbp == pytest.approx(180.0)


def test_respects_capacity_and_constant_market_commitments(
    battery_config: BatteryConfig,
) -> None:
    timeline = _timeline(
        {"Market 1": (5.0, 5.0, 5.0, 5.0, 50.0, 50.0, 50.0, 50.0)},
        {"Market 1": ONE_HOUR},
    )

    result = optimize_battery(timeline, battery_config)

    timestamps = result.timestamps
    assert timestamps == tuple(
        START_TIME + step * HALF_HOUR for step in range(8)
    )
    _assert_dense_results(result)

    for hour_start in (0, 2, 4, 6):
        assert result.charge_mw[
            ("Market 1", timestamps[hour_start])
        ] == pytest.approx(
            result.charge_mw[("Market 1", timestamps[hour_start + 1])]
        )
        assert result.discharge_mw[
            ("Market 1", timestamps[hour_start])
        ] == pytest.approx(
            result.discharge_mw[("Market 1", timestamps[hour_start + 1])]
        )

    low_period_charge_mwh = sum(
        result.charge_mw[("Market 1", timestamp)] * 0.5
        for timestamp in timestamps[:4]
    )
    assert low_period_charge_mwh == pytest.approx(8.0)
    assert all(
        result.charge_mw[("Market 1", timestamp)] == pytest.approx(0.0)
        for timestamp in timestamps[4:]
    )
    assert all(
        result.discharge_mw[("Market 1", timestamp)] == pytest.approx(5.0)
        for timestamp in timestamps[4:]
    )

    assert result.energy_mwh[timestamps[0]] == pytest.approx(2.0)
    assert result.energy_mwh[timestamps[4]] == pytest.approx(10.0)
    assert result.energy_mwh[timestamps[5]] == pytest.approx(7.5)
    assert result.energy_mwh[timestamps[6]] == pytest.approx(5.0)
    assert result.energy_mwh[timestamps[7]] == pytest.approx(2.5)
    assert result.total_profit_gbp == pytest.approx(460.0)


def test_allows_sale_of_initial_energy() -> None:
    timeline = _timeline(
        {"Market 1": (100.0,)},
        {"Market 1": HALF_HOUR},
    )

    result = optimize_battery(timeline)

    assert result.timestamps == (START_TIME,)
    _assert_dense_results(result)
    assert result.charge_mw[("Market 1", START_TIME)] == pytest.approx(0.0)
    assert result.discharge_mw[("Market 1", START_TIME)] == pytest.approx(4.0)
    assert result.energy_mwh[START_TIME] == pytest.approx(2.0)
    assert result.total_profit_gbp == pytest.approx(200.0)


def test_prevents_simultaneous_charge_and_discharge() -> None:
    timeline = _timeline(
        {
            "Market 1": (0.0, 0.0),
            "Market 2": (100.0, 100.0),
        },
        {"Market 1": HALF_HOUR, "Market 2": HALF_HOUR},
    )
    config = BatteryConfig(
        max_charge_mw=5.0,
        max_discharge_mw=5.0,
        storage_capacity_mwh=10.0,
        initial_energy_mwh=0.0,
    )

    result = optimize_battery(timeline, config)

    first_timestamp, second_timestamp = result.timestamps
    assert result.market_names == ("Market 1", "Market 2")
    _assert_dense_results(result)

    assert result.charge_mw[
        ("Market 1", first_timestamp)
    ] == pytest.approx(5.0)
    assert result.discharge_mw[
        ("Market 2", second_timestamp)
    ] == pytest.approx(5.0)

    for timestamp in result.timestamps:
        total_charge = sum(
            result.charge_mw[(market_name, timestamp)]
            for market_name in result.market_names
        )
        total_discharge = sum(
            result.discharge_mw[(market_name, timestamp)]
            for market_name in result.market_names
        )
        assert total_charge == pytest.approx(0.0) or (
            total_discharge == pytest.approx(0.0)
        )

    assert result.energy_mwh[first_timestamp] == pytest.approx(0.0)
    assert result.energy_mwh[second_timestamp] == pytest.approx(2.5)
    assert result.total_profit_gbp == pytest.approx(250.0)
