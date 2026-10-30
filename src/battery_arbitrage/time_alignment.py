import math
from bisect import bisect_right
from datetime import datetime, timedelta
from itertools import pairwise

from battery_arbitrage.domain import (
    MarketData,
    MarketIntervals,
    MarketPrices,
    MarketPricesAtTime,
    Timeline,
    TimelinePrices,
)

MICROSECOND = timedelta(microseconds=1)


def align_market_data(
    market_data: MarketData,
    market_intervals: MarketIntervals,
    tolerance_millis: int = 1000,
) -> Timeline:
    """
    Align multiple markets' prices to a common timeline.

    The common period is the greatest common divisor of all market intervals.
    Timestamps are normalized to a single grid anchored at the earliest
    timestamp across all markets. A market's price applies from its timestamp
    until the next timestamp, so longer intervals are repeated across the
    common-grid steps they cover. Only complete market intervals covered by
    every market are returned, so the timeline starts and ends on a boundary
    shared by every market.

    Args:
        market_data (MarketData): A dictionary mapping market names to their
            respective price dictionaries.
        market_intervals (MarketIntervals): A dictionary mapping market names to
            their respective intervals.
        tolerance_millis (int): Maximum timestamp deviation allowed when
            normalizing timestamps to the common grid.

    Returns:
        Timeline: The aligned prices, common period, and per-market intervals.

    Raises:
        ValueError: If markets are empty, market intervals do not match the
            market data, timestamps are misaligned, or no complete common
            coverage exists. The message names the offending market where
            applicable.
    """
    if not market_data:
        raise ValueError("Market data is empty")
    if set(market_data) != set(market_intervals):
        raise ValueError("Market intervals do not match the market data")
    if tolerance_millis < 0:
        raise ValueError("Tolerance must be non-negative")

    tolerance = timedelta(milliseconds=tolerance_millis)
    common_period = _common_period(market_intervals, market_data)

    origin = min(min(prices) for prices in market_data.values())
    normalized: dict[str, MarketPrices] = {}

    for market_name, market_prices in market_data.items():
        if not market_prices:
            raise ValueError(f"Market '{market_name}' has no timestamps")

        interval = market_intervals[market_name]
        normalized_prices: MarketPrices = {}
        for timestamp, price in market_prices.items():
            snapped = _snap_to_grid(
                market_name, timestamp, origin, common_period, tolerance
            )
            if snapped in normalized_prices:
                raise ValueError(
                    f"Market '{market_name}' has timestamps that normalize "
                    f"to the same grid point: {snapped!r}"
                )
            normalized_prices[snapped] = price

        timestamps = sorted(normalized_prices)
        for previous, current in pairwise(timestamps):
            if current - previous != interval:
                raise ValueError(
                    f"Market '{market_name}' timestamps do not match its "
                    f"declared interval"
                )
        normalized[market_name] = normalized_prices

    coverage_start, coverage_end = _common_coverage(
        normalized,
        market_intervals,
        origin,
        common_period,
    )

    timeline_prices = _build_timeline_prices(
        normalized,
        market_intervals,
        coverage_start,
        coverage_end,
        common_period,
    )
    return Timeline(
        prices=timeline_prices,
        common_period=common_period,
        market_intervals=dict(market_intervals),
    )


def _common_period(
    market_intervals: MarketIntervals, market_data: MarketData
) -> timedelta:
    common_microseconds = 0
    for market_name, interval in market_intervals.items():
        if interval <= timedelta(0):
            raise ValueError(
                f"Market '{market_name}' has a non-positive interval"
            )
        if not market_data[market_name]:
            raise ValueError(f"Market '{market_name}' has no timestamps")
        common_microseconds = math.gcd(
            common_microseconds, interval // MICROSECOND
        )
    return common_microseconds * MICROSECOND


def _common_coverage(
    normalized: dict[str, MarketPrices],
    market_intervals: MarketIntervals,
    origin: datetime,
    common_period: timedelta,
) -> tuple[datetime, datetime]:
    """Return the earliest and latest boundaries shared by every market."""
    start_indices: list[int] = []
    end_indices: list[int] = []
    step_sizes: list[int] = []

    for market_name, market_prices in normalized.items():
        timestamps = sorted(market_prices)
        interval = market_intervals[market_name]
        step = interval // common_period
        start_indices.append((timestamps[0] - origin) // common_period)
        end_indices.append(
            (timestamps[-1] + interval - origin) // common_period
        )
        step_sizes.append(step)

    lower = max(start_indices)
    upper = min(end_indices)
    if lower > upper:
        raise ValueError("Markets have no complete common coverage")

    candidate = lower
    while candidate <= upper:
        for start, step in zip(start_indices, step_sizes):
            if candidate < start:
                candidate = start
                break
            offset = (candidate - start) % step
            if offset:
                candidate += step - offset
                break
        else:
            break

    if candidate > upper:
        raise ValueError("Markets have no complete common coverage")

    period_steps = math.lcm(*step_sizes)
    end_candidate = (
        candidate + ((upper - candidate) // period_steps) * period_steps
    )
    if end_candidate <= candidate:
        raise ValueError("Markets have no complete common coverage")

    return (
        origin + candidate * common_period,
        origin + end_candidate * common_period,
    )


def _snap_to_grid(
    market_name: str,
    timestamp: datetime,
    origin: datetime,
    common_period: timedelta,
    tolerance: timedelta,
) -> datetime:
    offset = timestamp - origin
    period_microseconds = common_period // MICROSECOND
    offset_microseconds = offset // MICROSECOND
    steps = (offset_microseconds + period_microseconds // 2) // (
        period_microseconds
    )
    snapped = origin + steps * common_period
    if abs(timestamp - snapped) > tolerance:
        raise ValueError(
            f"Market '{market_name}' has timestamp {timestamp!r} that is "
            f"not aligned to the common grid"
        )
    return snapped


def _build_timeline_prices(
    normalized: dict[str, MarketPrices],
    market_intervals: MarketIntervals,
    coverage_start: datetime,
    coverage_end: datetime,
    common_period: timedelta,
) -> TimelinePrices:
    sorted_times = {
        market_name: sorted(market_prices)
        for market_name, market_prices in normalized.items()
    }
    timeline_prices: TimelinePrices = {}
    timestamp = coverage_start
    while timestamp + common_period <= coverage_end:
        prices_at_time: MarketPricesAtTime = {}
        for market_name, market_prices in normalized.items():
            market_times = sorted_times[market_name]
            index = bisect_right(market_times, timestamp) - 1
            if index < 0:
                raise ValueError(
                    f"Market '{market_name}' does not cover {timestamp!r}"
                )
            price_timestamp = market_times[index]
            if timestamp >= price_timestamp + market_intervals[market_name]:
                raise ValueError(
                    f"Market '{market_name}' does not cover {timestamp!r}"
                )
            prices_at_time[market_name] = market_prices[price_timestamp]
        timeline_prices[timestamp] = prices_at_time
        timestamp += common_period

    if not timeline_prices:
        raise ValueError("Markets have no complete common coverage")
    return timeline_prices
