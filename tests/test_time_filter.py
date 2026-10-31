from datetime import datetime, timedelta

import pytest

from battery_arbitrage.domain import Timeline
from battery_arbitrage.time_filter import select_timeline_period

START = datetime(2025, 1, 1)
HALF_HOUR = timedelta(minutes=30)
ONE_HOUR = timedelta(hours=1)


def _timeline() -> Timeline:
    return Timeline(
        prices={
            START + index * HALF_HOUR: {
                "Half-hourly": float(index),
                "Hourly": float(index // 2),
            }
            for index in range(8)
        },
        common_period=HALF_HOUR,
        market_intervals={"Half-hourly": HALF_HOUR, "Hourly": ONE_HOUR},
    )


def test_selects_half_open_period_on_shared_market_boundaries() -> None:
    timeline = _timeline()

    selected = select_timeline_period(
        timeline,
        START + ONE_HOUR,
        START + ONE_HOUR * 3,
    )

    assert selected.prices == {
        START + ONE_HOUR: {"Half-hourly": 2.0, "Hourly": 1.0},
        START + ONE_HOUR + HALF_HOUR: {
            "Half-hourly": 3.0,
            "Hourly": 1.0,
        },
        START + ONE_HOUR * 2: {"Half-hourly": 4.0, "Hourly": 2.0},
        START + ONE_HOUR * 2 + HALF_HOUR: {
            "Half-hourly": 5.0,
            "Hourly": 2.0,
        },
    }
    assert selected.common_period == timeline.common_period
    assert selected.market_intervals == timeline.market_intervals


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        (START + HALF_HOUR, START + ONE_HOUR * 2),
        (START, START + HALF_HOUR),
    ],
)
def test_rejects_period_boundaries_inside_hourly_market_interval(
    start_time: datetime,
    end_time: datetime,
) -> None:
    with pytest.raises(ValueError, match="market interval boundary"):
        select_timeline_period(_timeline(), start_time, end_time)


def test_clips_period_that_starts_before_timeline_coverage() -> None:
    selected = select_timeline_period(
        _timeline(), START - ONE_HOUR, START + ONE_HOUR
    )

    assert tuple(selected.prices) == (START, START + HALF_HOUR)


def test_clips_period_that_ends_after_timeline_coverage() -> None:
    selected = select_timeline_period(
        _timeline(), START + ONE_HOUR * 3, START + ONE_HOUR * 5
    )

    assert tuple(selected.prices) == (
        START + ONE_HOUR * 3,
        START + ONE_HOUR * 3 + HALF_HOUR,
    )


def test_period_wider_than_timeline_selects_all_available_timestamps() -> None:
    selected = select_timeline_period(
        _timeline(), START - ONE_HOUR, START + ONE_HOUR * 5
    )

    assert tuple(selected.prices) == tuple(_timeline().prices)


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        (START - ONE_HOUR * 2, START - ONE_HOUR),
        (START + ONE_HOUR * 5, START + ONE_HOUR * 6),
    ],
)
def test_rejects_period_with_no_timeline_overlap(
    start_time: datetime,
    end_time: datetime,
) -> None:
    with pytest.raises(ValueError, match="does not overlap"):
        select_timeline_period(_timeline(), start_time, end_time)


def test_reports_reversed_period_boundaries_clearly() -> None:
    with pytest.raises(ValueError, match="start_time must be earlier"):
        select_timeline_period(
            _timeline(),
            START + ONE_HOUR * 2,
            START + ONE_HOUR,
        )


def test_allows_one_sided_period_bound() -> None:
    timeline = _timeline()

    selected = select_timeline_period(
        timeline,
        start_time=START + ONE_HOUR * 2,
    )

    assert tuple(selected.prices) == (
        START + ONE_HOUR * 2,
        START + ONE_HOUR * 2 + HALF_HOUR,
        START + ONE_HOUR * 3,
        START + ONE_HOUR * 3 + HALF_HOUR,
    )
