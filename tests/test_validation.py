from datetime import datetime, timedelta

import pytest

from battery_arbitrage.domain import MarketData
from battery_arbitrage.validation import validate_market_data


def test_returns_interval_for_each_market() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30): 55.0,
            datetime(2025, 1, 1, 1, 0): 60.0,
        },
        "Market 2": {
            datetime(2025, 1, 1, 0, 0): 45.0,
            datetime(2025, 1, 1, 1, 0): 48.0,
            datetime(2025, 1, 1, 2, 0): 52.0,
        },
    }

    result = validate_market_data(market_data, tolerance_millis=0)

    assert result == {
        "Market 1": timedelta(minutes=30),
        "Market 2": timedelta(hours=1),
    }


def test_rejects_empty_market_data() -> None:
    with pytest.raises(ValueError):
        validate_market_data({}, tolerance_millis=0)


def test_rejects_negative_tolerance() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30): 55.0,
        }
    }

    with pytest.raises(
        ValueError, match="tolerance_millis must be non-negative"
    ):
        validate_market_data(market_data, tolerance_millis=-1)


def test_rejects_market_with_fewer_than_two_observations() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
        }
    }

    with pytest.raises(ValueError):
        validate_market_data(market_data, tolerance_millis=0)


def test_rejects_non_uniform_intervals() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30): 55.0,
            datetime(2025, 1, 1, 1, 15): 60.0,
        }
    }

    with pytest.raises(ValueError):
        validate_market_data(market_data, tolerance_millis=0)


def test_rejects_market_with_no_observations() -> None:
    market_data: MarketData = {"Market 1": {}}

    with pytest.raises(ValueError):
        validate_market_data(market_data, tolerance_millis=0)


def test_rejects_empty_market_among_valid_markets() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30): 55.0,
        },
        "Market 2": {},
    }

    with pytest.raises(ValueError):
        validate_market_data(market_data, tolerance_millis=0)


def test_accepts_timestamps_within_tolerance() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30, 0, 500_000): 55.0,
            datetime(2025, 1, 1, 1, 0, 0, 500_000): 60.0,
            datetime(2025, 1, 1, 1, 30, 0, 500_000): 65.0,
            datetime(2025, 1, 1, 2, 0, 0, 500_000): 70.0,
        }
    }

    result = validate_market_data(market_data, tolerance_millis=1000)

    assert result == {"Market 1": timedelta(minutes=30)}


def test_accepts_timestamps_at_tolerance_boundary() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30, 1): 55.0,
            datetime(2025, 1, 1, 1, 0, 1): 60.0,
            datetime(2025, 1, 1, 1, 30, 1): 65.0,
            datetime(2025, 1, 1, 2, 0, 1): 70.0,
        }
    }

    result = validate_market_data(market_data, tolerance_millis=1000)

    assert result == {"Market 1": timedelta(minutes=30)}


def test_returns_median_for_odd_interval_count() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30): 55.0,
            datetime(2025, 1, 1, 1, 0, 0, 500_000): 60.0,
            datetime(2025, 1, 1, 1, 30, 1, 500_000): 65.0,
            datetime(2025, 1, 1, 2, 0, 3): 70.0,
            datetime(2025, 1, 1, 2, 30, 5): 75.0,
        }
    }

    result = validate_market_data(market_data, tolerance_millis=1000)

    assert result == {"Market 1": timedelta(minutes=30, seconds=1)}


def test_rejects_timestamps_outside_tolerance() -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30, 1, 500_000): 55.0,
            datetime(2025, 1, 1, 1, 0, 1, 500_000): 60.0,
            datetime(2025, 1, 1, 1, 30, 1, 500_000): 65.0,
            datetime(2025, 1, 1, 2, 0, 1, 500_000): 70.0,
        }
    }

    with pytest.raises(ValueError):
        validate_market_data(market_data, tolerance_millis=1000)


@pytest.mark.parametrize(
    "invalid_price", [float("nan"), float("inf"), float("-inf")]
)
def test_rejects_non_finite_prices(invalid_price: float) -> None:
    market_data: MarketData = {
        "Market 1": {
            datetime(2025, 1, 1, 0, 0): 50.0,
            datetime(2025, 1, 1, 0, 30): invalid_price,
        }
    }

    with pytest.raises(ValueError):
        validate_market_data(market_data, tolerance_millis=0)
