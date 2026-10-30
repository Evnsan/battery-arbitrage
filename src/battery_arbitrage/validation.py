import math
from datetime import timedelta
from itertools import pairwise

from battery_arbitrage.domain import MarketData, MarketIntervals


def validate_market_data(
    market_data: MarketData, tolerance_millis: int
) -> MarketIntervals:
    """
    Validate market data and infer each market's interval.

    For each market, timestamps are sorted and consecutive differences are
    calculated. The inferred interval is the median (p50) of those differences,
    which reduces the influence of an isolated irregular interval. Every
    consecutive difference must be within tolerance_millis of the inferred
    interval.

    With very few intervals, the median can still mask an irregular interval.
    In particular, with only two intervals the median is their midpoint, so
    intervals that differ by up to twice the tolerance can pass.

    Args:
        market_data (MarketData): A dictionary mapping market names to their
            respective price dictionaries.
        tolerance_millis (int): Maximum allowed absolute deviation, in
            milliseconds, between a consecutive timestamp difference and the
            inferred interval. The comparison is inclusive.

    Returns:
        MarketIntervals: A dictionary mapping each market name to its inferred
            interval.

    Raises:
        ValueError: If tolerance_millis is negative, market data is empty, a
            market has fewer than two observations, a market contains a
            non-finite price, or a market's consecutive timestamp differences
            are not uniform within the tolerance. For market-specific errors,
            the message names the offending market.
    """
    if tolerance_millis < 0:
        raise ValueError("tolerance_millis must be non-negative")

    if not market_data:
        raise ValueError("Market data is empty")

    tolerance = timedelta(milliseconds=tolerance_millis)
    market_intervals: MarketIntervals = {}

    for market_name, market_prices in market_data.items():
        if len(market_prices) < 2:
            raise ValueError(
                f"Market '{market_name}' has fewer than two observations"
            )

        for price in market_prices.values():
            if not math.isfinite(price):
                raise ValueError(
                    f"Market '{market_name}' contains a non-finite price"
                )

        timestamps = sorted(market_prices)
        intervals = [
            current - previous for previous, current in pairwise(timestamps)
        ]

        # Calculate the median interval to mitigate the effect of outliers
        sorted_intervals = sorted(intervals)
        middle = len(sorted_intervals) // 2
        if len(sorted_intervals) % 2:
            interval = sorted_intervals[middle]
        else:
            interval = (
                sorted_intervals[middle - 1] + sorted_intervals[middle]
            ) / 2

        for delta in intervals:
            if abs(delta - interval) > tolerance:
                raise ValueError(
                    f"Market '{market_name}' has non-uniform timestamp "
                    f"intervals"
                )

        market_intervals[market_name] = interval

    return market_intervals
