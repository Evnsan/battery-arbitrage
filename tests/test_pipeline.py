from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from openpyxl import Workbook  # type: ignore[import-untyped]

from battery_arbitrage import pipeline
from battery_arbitrage.domain import BatteryConfig, Timeline

START = datetime(2025, 1, 1)
HALF_HOUR = timedelta(minutes=30)
ONE_HOUR = timedelta(hours=1)


def _write_workbook(path: Path, observations: int = 4) -> None:
    workbook = Workbook()
    half_hourly = workbook.active
    half_hourly.title = "Half-hourly data"
    half_hourly.append(["Timestamp", "Market 1 Price [£/MWh]"])
    for index in range(observations):
        half_hourly.append([START + index * HALF_HOUR, 50.0])

    hourly = workbook.create_sheet("Hourly data")
    hourly.append(["Timestamp", "Market 2 Price [£/MWh]"])
    for index in range(2):
        hourly.append([START + index * ONE_HOUR, 50.0])
    workbook.save(path)


def test_forwards_stages_in_order_and_returns_report_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "markets.xlsx"
    market_data = {"market": {START: 50.0}}
    intervals = {"market": HALF_HOUR}
    timeline = Timeline(
        prices={START: {"market": 50.0}},
        common_period=HALF_HOUR,
        market_intervals=intervals,
    )
    solution = object()
    report = object()
    calls: list[tuple[object, ...]] = []

    def parse_market_data(file_path: Path) -> object:
        calls.append(("parse", file_path))
        return market_data

    def validate_market_data(data: object, tolerance_millis: int) -> object:
        calls.append(("validate", data, tolerance_millis))
        return intervals

    def align_market_data(
        data: object, market_intervals: object, tolerance_millis: int
    ) -> object:
        calls.append(("align", data, market_intervals, tolerance_millis))
        return timeline

    def optimize_battery(
        aligned_timeline: object, config: BatteryConfig | None
    ) -> object:
        calls.append(("optimize", aligned_timeline, config))
        return solution

    def build_report(
        optimization_result: object, aligned_timeline: object
    ) -> object:
        calls.append(("report", optimization_result, aligned_timeline))
        return report

    monkeypatch.setattr(pipeline, "parse_market_data", parse_market_data)
    monkeypatch.setattr(pipeline, "validate_market_data", validate_market_data)
    monkeypatch.setattr(pipeline, "align_market_data", align_market_data)
    monkeypatch.setattr(pipeline, "optimize_battery", optimize_battery)
    monkeypatch.setattr(pipeline, "build_report", build_report)

    result = pipeline.run_optimization(path)

    assert result is report
    assert calls == [
        ("parse", path),
        ("validate", market_data, 1000),
        ("align", market_data, intervals, 1000),
        ("optimize", timeline, None),
        ("report", solution, timeline),
    ]


def test_forwards_custom_config_and_tolerance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "markets.xlsx"
    data = {"market": {START: 50.0}}
    intervals = {"market": HALF_HOUR}
    timeline = object()
    config = BatteryConfig(4.0, 3.0, 8.0, 1.0)
    tolerance = 250
    calls: list[tuple[object, ...]] = []

    monkeypatch.setattr(pipeline, "parse_market_data", lambda _: data)
    def validate(data: object, actual_tolerance: int) -> object:
        calls.append(("validate", data, actual_tolerance))
        return intervals

    def align(
        actual_data: object,
        actual_intervals: object,
        actual_tolerance: int,
    ) -> object:
        calls.append(("align", actual_data, actual_intervals, actual_tolerance))
        return timeline

    def optimize(actual_timeline: object, actual_config: object) -> object:
        calls.append(("optimize", actual_timeline, actual_config))
        return object()

    monkeypatch.setattr(pipeline, "validate_market_data", validate)
    monkeypatch.setattr(pipeline, "align_market_data", align)
    monkeypatch.setattr(pipeline, "optimize_battery", optimize)
    monkeypatch.setattr(pipeline, "build_report", lambda *_: "report")

    assert pipeline.run_optimization(path, config, tolerance) == "report"
    assert calls == [
        ("validate", data, tolerance),
        ("align", data, intervals, tolerance),
        ("optimize", timeline, config),
    ]


def test_selects_requested_period_before_optimization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "markets.xlsx"
    start_time = START + ONE_HOUR
    end_time = START + ONE_HOUR * 2
    aligned_timeline = Timeline(
        prices={START: {"market": 50.0}},
        common_period=HALF_HOUR,
        market_intervals={"market": HALF_HOUR},
    )
    selected_timeline = object()
    calls: list[tuple[object, ...]] = []

    def parse(_: Path) -> object:
        calls.append(("parse",))
        return object()

    def validate(data: object, tolerance: int) -> object:
        calls.append(("validate", tolerance))
        return object()

    def align(data: object, intervals: object, tolerance: int) -> object:
        calls.append(("align", tolerance))
        return aligned_timeline

    def select(
        timeline: object,
        actual_start: datetime | None,
        actual_end: datetime | None,
    ) -> object:
        calls.append(("select", timeline, actual_start, actual_end))
        return selected_timeline

    def optimize(timeline: object, config: BatteryConfig | None) -> object:
        calls.append(("optimize", timeline))
        return object()

    monkeypatch.setattr(pipeline, "parse_market_data", parse)
    monkeypatch.setattr(pipeline, "validate_market_data", validate)
    monkeypatch.setattr(pipeline, "align_market_data", align)
    monkeypatch.setattr(pipeline, "select_timeline_period", select)
    monkeypatch.setattr(pipeline, "optimize_battery", optimize)
    monkeypatch.setattr(pipeline, "build_report", lambda *_: "report")

    assert pipeline.run_optimization(
        path, start_time=start_time, end_time=end_time
    ) == "report"
    assert calls == [
        ("parse",),
        ("validate", 1000),
        ("align", 1000),
        ("select", aligned_timeline, start_time, end_time),
        ("optimize", selected_timeline),
    ]


@pytest.mark.parametrize(
    ("failed_stage", "expected_calls"),
    [
        ("parse", ["parse"]),
        ("validate", ["parse", "validate"]),
        ("align", ["parse", "validate", "align"]),
        ("optimize", ["parse", "validate", "align", "optimize"]),
        (
            "report",
            ["parse", "validate", "align", "optimize", "report"],
        ),
    ],
)
def test_stage_errors_propagate_and_stop_later_stages(
    failed_stage: str,
    expected_calls: list[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "markets.xlsx"
    error = RuntimeError(f"{failed_stage} failed")
    calls: list[str] = []

    def stage(name: str, result: object) -> Callable[..., object]:
        def run(*_args: object, **_kwargs: object) -> object:
            calls.append(name)
            if name == failed_stage:
                raise error
            return result

        return run

    monkeypatch.setattr(pipeline, "parse_market_data", stage("parse", {}))
    monkeypatch.setattr(
        pipeline, "validate_market_data", stage("validate", {})
    )
    monkeypatch.setattr(pipeline, "align_market_data", stage("align", object()))
    monkeypatch.setattr(
        pipeline, "optimize_battery", stage("optimize", object())
    )
    monkeypatch.setattr(pipeline, "build_report", stage("report", object()))

    with pytest.raises(RuntimeError) as raised:
        pipeline.run_optimization(path)

    assert raised.value is error
    assert calls == expected_calls


def test_run_optimization_builds_integrated_report(tmp_path: Path) -> None:
    path = tmp_path / "constant-prices.xlsx"
    _write_workbook(path)

    report = pipeline.run_optimization(path)

    assert len(report.dispatch_rows) == 8
    assert len(report.operation_rows) == 4
    assert all(row.price == 50.0 for row in report.dispatch_rows)
    assert report.total_profit_gbp == pytest.approx(100.0)
    assert report.operation_rows[-1].cumulative_cash_flow_gbp == pytest.approx(
        100.0
    )
    dispatch_cash_flow = sum(row.cash_flow_gbp for row in report.dispatch_rows)
    assert dispatch_cash_flow == pytest.approx(report.total_profit_gbp)
    assert all(0.0 <= row.energy_mwh <= 10.0 for row in report.operation_rows)


def test_run_optimization_uses_only_requested_period(
    tmp_path: Path,
) -> None:
    path = tmp_path / "constant-prices.xlsx"
    _write_workbook(path)

    report = pipeline.run_optimization(
        path,
        start_time=START + ONE_HOUR,
        end_time=START + ONE_HOUR * 2,
    )

    assert len(report.dispatch_rows) == 4
    assert len(report.operation_rows) == 2
    assert all(
        START + ONE_HOUR <= row.timestamp < START + ONE_HOUR * 2
        for row in report.operation_rows
    )
    assert report.total_profit_gbp == pytest.approx(100.0)


def test_missing_workbook_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pipeline.run_optimization(tmp_path / "missing.xlsx")


def test_workbook_with_too_few_observations_raises_value_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "too-few-observations.xlsx"
    _write_workbook(path, observations=1)

    with pytest.raises(ValueError):
        pipeline.run_optimization(path)
