from datetime import datetime, timedelta

import pytest

from battery_arbitrage.domain import OptimizationResult, Timeline
from battery_arbitrage.reporting import build_report

START = datetime(2025, 1, 1)
HALF_HOUR = timedelta(minutes=30)


def _result(
    timestamps: tuple[datetime, ...],
    markets: tuple[str, ...],
    charge: dict[tuple[str, datetime], float],
    discharge: dict[tuple[str, datetime], float],
    energy: dict[datetime, float],
    profit: float,
    timestep: timedelta = HALF_HOUR,
) -> OptimizationResult:
    return OptimizationResult(
        timestamps=timestamps,
        market_names=markets,
        timestep=timestep,
        charge_mw=charge,
        discharge_mw=discharge,
        energy_mwh=energy,
        total_profit_gbp=profit,
    )


def test_builds_dispatch_rows_for_each_market_and_timestep() -> None:
    t0, t1 = START, START + HALF_HOUR
    timeline = Timeline(
        prices={
            t0: {"Market B": 20.0, "Market A": 10.0},
            t1: {"Market B": 30.0, "Market A": 40.0},
        },
        common_period=HALF_HOUR,
        market_intervals={"Market A": HALF_HOUR, "Market B": HALF_HOUR},
    )
    solution = _result(
        (t0, t1),
        ("Market B", "Market A"),
        {
            ("Market A", t0): 2.0,
            ("Market B", t0): 0.0,
            ("Market A", t1): 0.0,
            ("Market B", t1): 1.0,
        },
        {
            ("Market A", t0): 0.0,
            ("Market B", t0): 1.0,
            ("Market A", t1): 0.0,
            ("Market B", t1): 0.0,
        },
        {t0: 5.0, t1: 4.5},
        -15.0,
    )

    report = build_report(solution, timeline)

    assert [
        (row.timestamp, row.market_name) for row in report.dispatch_rows
    ] == [
        (t0, "Market A"),
        (t0, "Market B"),
        (t1, "Market A"),
        (t1, "Market B"),
    ]
    assert [
        (row.price, row.charge_mw, row.discharge_mw, row.cash_flow_gbp)
        for row in report.dispatch_rows
    ] == [
        (10.0, 2.0, 0.0, -10.0),
        (20.0, 0.0, 1.0, 10.0),
        (40.0, 0.0, 0.0, 0.0),
        (30.0, 1.0, 0.0, -15.0),
    ]


def test_retains_zero_valued_dispatch_rows() -> None:
    timeline = Timeline(
        prices={START: {"Market A": 25.0}},
        common_period=HALF_HOUR,
        market_intervals={"Market A": HALF_HOUR},
    )
    solution = _result(
        (START,),
        ("Market A",),
        {("Market A", START): 0.0},
        {("Market A", START): 0.0},
        {START: 2.0},
        0.0,
    )

    report = build_report(solution, timeline)

    assert len(report.dispatch_rows) == 1
    assert report.dispatch_rows[0].charge_mw == 0.0
    assert report.dispatch_rows[0].discharge_mw == 0.0
    assert report.dispatch_rows[0].cash_flow_gbp == 0.0


def test_builds_operation_rows_with_aggregates_and_running_cash_flow() -> None:
    t0, t1 = START, START + HALF_HOUR
    timeline = Timeline(
        prices={t0: {"A": 10.0, "B": 30.0}, t1: {"A": 50.0, "B": 20.0}},
        common_period=HALF_HOUR,
        market_intervals={"A": HALF_HOUR, "B": HALF_HOUR},
    )
    solution = _result(
        (t0, t1),
        ("A", "B"),
        {("A", t0): 2.0, ("B", t0): 0.0, ("A", t1): 0.0, ("B", t1): 0.0},
        {("A", t0): 0.0, ("B", t0): 1.0, ("A", t1): 0.0, ("B", t1): 2.0},
        {t0: 3.0, t1: 3.5},
        25.0,
    )

    report = build_report(solution, timeline)

    assert [
        (
            row.timestamp,
            row.charge_mw,
            row.discharge_mw,
            row.energy_mwh,
            row.cash_flow_gbp,
            row.cumulative_cash_flow_gbp,
        )
        for row in report.operation_rows
    ] == [(t0, 2.0, 1.0, 3.0, 5.0, 5.0), (t1, 0.0, 2.0, 3.5, 20.0, 25.0)]


def test_apportions_hourly_commitment_across_half_hour_steps() -> None:
    t0, t1 = START, START + HALF_HOUR
    timeline = Timeline(
        prices={t0: {"Hourly": 50.0}, t1: {"Hourly": 50.0}},
        common_period=HALF_HOUR,
        market_intervals={"Hourly": timedelta(hours=1)},
    )
    solution = _result(
        (t0, t1),
        ("Hourly",),
        {("Hourly", t0): 0.0, ("Hourly", t1): 0.0},
        {("Hourly", t0): 4.0, ("Hourly", t1): 4.0},
        {t0: 8.0, t1: 6.0},
        200.0,
    )

    report = build_report(solution, timeline)

    assert [row.discharge_mw for row in report.dispatch_rows] == [4.0, 4.0]
    assert [row.cash_flow_gbp for row in report.dispatch_rows] == [100.0, 100.0]
    assert sum(row.cash_flow_gbp for row in report.dispatch_rows) == 200.0


def test_sorts_unsorted_result_inputs_deterministically() -> None:
    t0, t1 = START, START + HALF_HOUR
    timeline = Timeline(
        prices={t1: {"Z": 2.0, "A": 1.0}, t0: {"Z": 2.0, "A": 1.0}},
        common_period=HALF_HOUR,
        market_intervals={"A": HALF_HOUR, "Z": HALF_HOUR},
    )
    solution = _result(
        (t1, t0),
        ("Z", "A"),
        {(name, time): 0.0 for name in ("Z", "A") for time in (t1, t0)},
        {(name, time): 0.0 for name in ("Z", "A") for time in (t1, t0)},
        {t1: 3.0, t0: 3.0},
        0.0,
    )

    report = build_report(solution, timeline)

    assert [
        (row.timestamp, row.market_name) for row in report.dispatch_rows
    ] == [(t0, "A"), (t0, "Z"), (t1, "A"), (t1, "Z")]
    assert [row.timestamp for row in report.operation_rows] == [t0, t1]


def test_final_cumulative_cash_flow_matches_total_profit() -> None:
    timeline = Timeline(
        prices={START: {"A": 40.0}},
        common_period=HALF_HOUR,
        market_intervals={"A": HALF_HOUR},
    )
    solution = _result(
        (START,),
        ("A",),
        {("A", START): 0.0},
        {("A", START): 2.0},
        {START: 4.0},
        40.0,
    )

    report = build_report(solution, timeline)

    assert report.operation_rows[-1].cumulative_cash_flow_gbp == pytest.approx(
        report.total_profit_gbp
    )
