from datetime import datetime, timedelta

import pytest

from battery_arbitrage.domain import MarketData, MarketIntervals, Timeline
from battery_arbitrage.time_alignment import align_market_data

START_TIME = datetime(2025, 1, 1, 0, 0)
QUARTER_HOUR = timedelta(minutes=15)
HALF_HOUR = timedelta(minutes=30)
THREE_QUARTERS = timedelta(minutes=45)
ONE_HOUR = timedelta(hours=1)
TWO_HOURS = timedelta(hours=2)


def test_repeats_price_until_next_market_timestamp() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 48.47,
            START_TIME + ONE_HOUR: 49.00,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + HALF_HOUR: 20.0,
            START_TIME + ONE_HOUR: 30.0,
            START_TIME + HALF_HOUR * 3: 40.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": ONE_HOUR,
        "Market 2": HALF_HOUR,
    }

    timeline = align_market_data(market_data, market_intervals)

    assert timeline == Timeline(
        prices={
            START_TIME: {"Market 1": 48.47, "Market 2": 10.0},
            START_TIME + HALF_HOUR: {"Market 1": 48.47, "Market 2": 20.0},
            START_TIME + ONE_HOUR: {"Market 1": 49.00, "Market 2": 30.0},
            START_TIME + HALF_HOUR * 3: {
                "Market 1": 49.00,
                "Market 2": 40.0,
            },
        },
        common_period=HALF_HOUR,
        market_intervals={
            "Market 1": ONE_HOUR,
            "Market 2": HALF_HOUR,
        },
    )
    assert list(timeline.prices) == sorted(timeline.prices)


def test_uses_greatest_common_divisor_as_common_period() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
            START_TIME + ONE_HOUR: 3.0,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + THREE_QUARTERS: 20.0,
            START_TIME + THREE_QUARTERS * 2: 30.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": THREE_QUARTERS,
    }

    timeline = align_market_data(market_data, market_intervals)

    assert timeline.common_period == QUARTER_HOUR
    assert timeline.prices == {
        START_TIME: {"Market 1": 1.0, "Market 2": 10.0},
        START_TIME + QUARTER_HOUR: {"Market 1": 1.0, "Market 2": 10.0},
        START_TIME + HALF_HOUR: {"Market 1": 2.0, "Market 2": 10.0},
        START_TIME + THREE_QUARTERS: {"Market 1": 2.0, "Market 2": 20.0},
        START_TIME + ONE_HOUR: {"Market 1": 3.0, "Market 2": 20.0},
        START_TIME + QUARTER_HOUR * 5: {"Market 1": 3.0, "Market 2": 20.0},
    }


def test_timeline_preserves_market_intervals() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
            START_TIME + ONE_HOUR: 3.0,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + THREE_QUARTERS: 20.0,
            START_TIME + THREE_QUARTERS * 2: 30.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": THREE_QUARTERS,
    }

    timeline = align_market_data(market_data, market_intervals)

    assert timeline.market_intervals == market_intervals
    assert timeline.common_period == QUARTER_HOUR
    assert all(
        interval % timeline.common_period == timedelta(0)
        for interval in timeline.market_intervals.values()
    )


def test_timeline_does_not_alias_input_intervals() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
        }
    }
    market_intervals: MarketIntervals = {"Market 1": HALF_HOUR}

    timeline = align_market_data(market_data, market_intervals)
    market_intervals["Market 1"] = ONE_HOUR

    assert timeline.market_intervals == {"Market 1": HALF_HOUR}


def test_intersects_market_coverage() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
            START_TIME + ONE_HOUR: 3.0,
            START_TIME + HALF_HOUR * 3: 4.0,
        },
        "Market 2": {
            START_TIME + ONE_HOUR: 10.0,
            START_TIME + ONE_HOUR * 2: 20.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": ONE_HOUR,
    }

    timeline = align_market_data(market_data, market_intervals)

    assert timeline.prices == {
        START_TIME + ONE_HOUR: {"Market 1": 3.0, "Market 2": 10.0},
        START_TIME + HALF_HOUR * 3: {"Market 1": 4.0, "Market 2": 10.0},
    }
    assert timeline.common_period == HALF_HOUR


def test_trims_to_first_common_market_boundary() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + TWO_HOURS: 2.0,
            START_TIME + TWO_HOURS * 2: 3.0,
        },
        "Market 2": {
            START_TIME + ONE_HOUR: 10.0,
            START_TIME + TWO_HOURS: 20.0,
            START_TIME + ONE_HOUR * 3: 30.0,
            START_TIME + ONE_HOUR * 4: 40.0,
        },
        "Market 3": {
            START_TIME + ONE_HOUR * i: 100.0 + i for i in range(5)
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": TWO_HOURS,
        "Market 2": ONE_HOUR,
        "Market 3": ONE_HOUR,
    }

    timeline = align_market_data(market_data, market_intervals)

    assert timeline.prices == {
        START_TIME + TWO_HOURS: {
            "Market 1": 2.0,
            "Market 2": 20.0,
            "Market 3": 102.0,
        },
        START_TIME + ONE_HOUR * 3: {
            "Market 1": 2.0,
            "Market 2": 30.0,
            "Market 3": 103.0,
        },
    }

    coverage_start = min(timeline.prices)
    coverage_end = max(timeline.prices) + timeline.common_period
    for market_name, interval in market_intervals.items():
        first_timestamp = min(market_data[market_name])
        assert (coverage_start - first_timestamp) % interval == timedelta(0)
        assert (coverage_end - first_timestamp) % interval == timedelta(0)


def test_trims_partial_final_interval_to_common_boundary() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
            START_TIME + ONE_HOUR: 3.0,
            START_TIME + HALF_HOUR * 3: 4.0,
            START_TIME + ONE_HOUR * 2: 5.0,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + ONE_HOUR: 20.0,
            START_TIME + ONE_HOUR * 2: 30.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": ONE_HOUR,
    }

    timeline = align_market_data(market_data, market_intervals)

    assert timeline.prices == {
        START_TIME: {"Market 1": 1.0, "Market 2": 10.0},
        START_TIME + HALF_HOUR: {"Market 1": 2.0, "Market 2": 10.0},
        START_TIME + ONE_HOUR: {"Market 1": 3.0, "Market 2": 20.0},
        START_TIME + HALF_HOUR * 3: {"Market 1": 4.0, "Market 2": 20.0},
    }


def test_rejects_staggered_intervals_without_common_boundary() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + TWO_HOURS: 2.0,
            START_TIME + TWO_HOURS * 2: 3.0,
        },
        "Market 2": {
            START_TIME + ONE_HOUR: 10.0,
            START_TIME + ONE_HOUR * 3: 20.0,
            START_TIME + ONE_HOUR * 5: 30.0,
        },
        "Market 3": {
            START_TIME + ONE_HOUR * i: 100.0 + i for i in range(6)
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": TWO_HOURS,
        "Market 2": TWO_HOURS,
        "Market 3": ONE_HOUR,
    }

    with pytest.raises(ValueError, match="complete common coverage"):
        align_market_data(market_data, market_intervals)


def test_extends_each_market_final_interval() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
            START_TIME + ONE_HOUR: 3.0,
            START_TIME + HALF_HOUR * 3: 4.0,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + ONE_HOUR: 20.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": ONE_HOUR,
    }

    timeline = align_market_data(market_data, market_intervals)

    assert timeline.prices == {
        START_TIME: {"Market 1": 1.0, "Market 2": 10.0},
        START_TIME + HALF_HOUR: {"Market 1": 2.0, "Market 2": 10.0},
        START_TIME + ONE_HOUR: {"Market 1": 3.0, "Market 2": 20.0},
        START_TIME + HALF_HOUR * 3: {"Market 1": 4.0, "Market 2": 20.0},
    }


def test_single_market_uses_its_own_interval() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + ONE_HOUR: 2.0,
        }
    }
    market_intervals: MarketIntervals = {"Market 1": ONE_HOUR}

    timeline = align_market_data(market_data, market_intervals)

    assert timeline == Timeline(
        prices={
            START_TIME: {"Market 1": 1.0},
            START_TIME + ONE_HOUR: {"Market 1": 2.0},
        },
        common_period=ONE_HOUR,
        market_intervals={"Market 1": ONE_HOUR},
    )


def test_normalizes_timestamps_within_tolerance() -> None:
    offset = timedelta(milliseconds=500)
    market_data: MarketData = {
        "Market 1": {
            START_TIME + offset: 1.0,
            START_TIME + HALF_HOUR + offset: 2.0,
            START_TIME + ONE_HOUR + offset: 3.0,
            START_TIME + HALF_HOUR * 3 + offset: 4.0,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + ONE_HOUR: 20.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": ONE_HOUR,
    }

    timeline = align_market_data(
        market_data, market_intervals, tolerance_millis=1000
    )

    assert timeline.prices == {
        START_TIME: {"Market 1": 1.0, "Market 2": 10.0},
        START_TIME + HALF_HOUR: {"Market 1": 2.0, "Market 2": 10.0},
        START_TIME + ONE_HOUR: {"Market 1": 3.0, "Market 2": 20.0},
        START_TIME + HALF_HOUR * 3: {"Market 1": 4.0, "Market 2": 20.0},
    }


def test_accepts_timestamp_at_tolerance_boundary() -> None:
    offset = timedelta(milliseconds=1000)
    market_data: MarketData = {
        "Market 1": {
            START_TIME + offset: 1.0,
            START_TIME + HALF_HOUR + offset: 2.0,
            START_TIME + ONE_HOUR + offset: 3.0,
            START_TIME + HALF_HOUR * 3 + offset: 4.0,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + ONE_HOUR: 20.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": ONE_HOUR,
    }

    timeline = align_market_data(
        market_data, market_intervals, tolerance_millis=1000
    )

    assert timeline.prices == {
        START_TIME: {"Market 1": 1.0, "Market 2": 10.0},
        START_TIME + HALF_HOUR: {"Market 1": 2.0, "Market 2": 10.0},
        START_TIME + ONE_HOUR: {"Market 1": 3.0, "Market 2": 20.0},
        START_TIME + HALF_HOUR * 3: {"Market 1": 4.0, "Market 2": 20.0},
    }


def test_rejects_timestamp_outside_tolerance() -> None:
    offset = timedelta(milliseconds=1001)
    market_data: MarketData = {
        "Market 1": {
            START_TIME + offset: 1.0,
            START_TIME + HALF_HOUR + offset: 2.0,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + ONE_HOUR: 20.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": ONE_HOUR,
    }

    with pytest.raises(ValueError, match="Market 1"):
        align_market_data(market_data, market_intervals, tolerance_millis=1000)


def test_rejects_empty_market_data() -> None:
    with pytest.raises(ValueError):
        align_market_data({}, {})


def test_rejects_market_with_no_timestamps() -> None:
    market_data: MarketData = {"Market 1": {}}
    market_intervals: MarketIntervals = {"Market 1": HALF_HOUR}

    with pytest.raises(ValueError):
        align_market_data(market_data, market_intervals)


@pytest.mark.parametrize(
    ("market_data", "market_intervals"),
    [
        pytest.param(
            {
                "Market 1": {START_TIME: 1.0, START_TIME + HALF_HOUR: 2.0},
                "Market 2": {START_TIME: 3.0, START_TIME + ONE_HOUR: 4.0},
            },
            {"Market 1": HALF_HOUR},
            id="missing-interval",
        ),
        pytest.param(
            {"Market 1": {START_TIME: 1.0, START_TIME + HALF_HOUR: 2.0}},
            {"Market 1": HALF_HOUR, "Market 2": ONE_HOUR},
            id="extra-interval",
        ),
    ],
)
def test_rejects_mismatched_market_intervals(
    market_data: MarketData, market_intervals: MarketIntervals
) -> None:
    with pytest.raises(ValueError):
        align_market_data(market_data, market_intervals)


@pytest.mark.parametrize("interval", [timedelta(0), -HALF_HOUR])
def test_rejects_non_positive_market_interval(interval: timedelta) -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
        }
    }
    market_intervals: MarketIntervals = {"Market 1": interval}

    with pytest.raises(ValueError):
        align_market_data(market_data, market_intervals)


def test_rejects_data_not_matching_declared_interval() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
            START_TIME + ONE_HOUR: 3.0,
            START_TIME + HALF_HOUR * 3: 4.0,
        },
        "Market 2": {
            START_TIME: 10.0,
            START_TIME + ONE_HOUR: 20.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": HALF_HOUR,
    }

    with pytest.raises(ValueError):
        align_market_data(market_data, market_intervals)


def test_rejects_markets_with_no_common_coverage() -> None:
    market_data: MarketData = {
        "Market 1": {
            START_TIME: 1.0,
            START_TIME + HALF_HOUR: 2.0,
        },
        "Market 2": {
            START_TIME + ONE_HOUR * 2: 10.0,
            START_TIME + ONE_HOUR * 3: 20.0,
        },
    }
    market_intervals: MarketIntervals = {
        "Market 1": HALF_HOUR,
        "Market 2": ONE_HOUR,
    }

    with pytest.raises(ValueError):
        align_market_data(market_data, market_intervals)
