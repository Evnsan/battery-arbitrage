from battery_arbitrage.domain import MarketData, MarketIntervals, Timeline


def align_market_data(
    market_data: MarketData,
    market_intervals: MarketIntervals,
    tolerance_millis: int = 1000,
) -> Timeline:
    """
    Align multiple markets' prices to a common timeline.

    Args:
        market_data (MarketData): A dictionary mapping market names to their
            respective price dictionaries.
        market_intervals (MarketIntervals): A dictionary mapping market names to
            their respective intervals.
        tolerance_millis (int): Maximum timestamp deviation allowed when
            normalizing timestamps to each market's provided interval grid.

    Returns:
        Timeline: The aligned prices and common period.

    Raises:
        ValueError: If markets are empty, market intervals do not match the
            market data, intervals are incompatible, timestamps are misaligned,
            or no common coverage exists.
    """
    raise NotImplementedError("align_market_data is not implemented yet")
