from datetime import datetime, timedelta

from battery_arbitrage.domain import Timeline


def select_timeline_period(
    timeline: Timeline,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> Timeline:
    """Select a half-open period on shared market interval boundaries."""
    if not timeline.prices:
        raise ValueError("Timeline has no prices")
    if timeline.common_period <= timedelta(0):
        raise ValueError("Timeline common period must be positive")

    first_timestamp = min(timeline.prices)
    last_timestamp = max(timeline.prices)
    coverage_end = last_timestamp + timeline.common_period

    timeline_is_aware = first_timestamp.utcoffset() is not None
    for boundary in (start_time, end_time):
        if (
            boundary is not None
            and (boundary.utcoffset() is not None) != timeline_is_aware
        ):
            raise ValueError(
                "Time bounds must use the same timezone awareness as "
                "timeline timestamps"
            )

    if start_time is not None and end_time is not None:
        if start_time >= end_time:
            raise ValueError("start_time must be earlier than end_time")

    requested_start = first_timestamp if start_time is None else start_time
    requested_end = coverage_end if end_time is None else end_time
    selected_start = max(first_timestamp, requested_start)
    selected_end = min(coverage_end, requested_end)
    if selected_start >= selected_end:
        raise ValueError("Selected period does not overlap timeline coverage")

    for boundary in (selected_start, selected_end):
        for market_name, interval in timeline.market_intervals.items():
            if interval <= timedelta(0):
                raise ValueError(
                    f"Market '{market_name}' interval must be positive"
                )
            if (boundary - first_timestamp) % interval:
                raise ValueError(
                    "Selected period boundaries must match a market "
                    "interval boundary"
                )

    selected_prices = {
        timestamp: timeline.prices[timestamp]
        for timestamp in sorted(timeline.prices)
        if selected_start <= timestamp < selected_end
    }
    if not selected_prices:
        raise ValueError("Selected period contains no physical timesteps")

    return Timeline(
        prices=selected_prices,
        common_period=timeline.common_period,
        market_intervals=dict(timeline.market_intervals),
    )
