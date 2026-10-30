from battery_arbitrage.domain import MarketData, MarketIntervals


def validate_market_data(
    market_data: MarketData, tolerance_millis: int
) -> MarketIntervals:
    """
    Validate timestamps and prices in a market's price dictionary.

    Args:
        market_data (MarketData): A dictionary mapping market names to their
            respective price dictionaries.
        tolerance_millis (int): Maximum allowed deviation in milliseconds for
            uniform timestamp intervals.

    Returns:
        MarketIntervals: A dictionary mapping market names to their inferred
            intervals.

    Raises:
        ValueError: If the data is empty, contains invalid values,
            has fewer than two observations, or has non-uniform
            timestamp intervals.
    """
    raise NotImplementedError("validate_market_data is not implemented yet")
