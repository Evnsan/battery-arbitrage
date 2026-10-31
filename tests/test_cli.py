from datetime import datetime
from pathlib import Path

import pytest

from battery_arbitrage import cli
from battery_arbitrage.domain import DispatchReport


def _report() -> DispatchReport:
    return DispatchReport(
        dispatch_rows=(), operation_rows=(), total_profit_gbp=0.0
    )


def test_optimize_command_uses_default_csv_paths(
    monkeypatch, tmp_path: Path
) -> None:
    input_path = tmp_path / "market-data.xlsx"
    report = _report()
    calls: list[tuple[object, ...]] = []
    log_settings: list[tuple[object, ...]] = []

    def run_optimization(
        file_path: Path,
        config: object,
        tolerance_millis: int,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> object:
        calls.append(
            (
                "optimize",
                file_path,
                config,
                tolerance_millis,
                start_time,
                end_time,
            )
        )
        return report

    def write_report_csv(
        actual_report: object,
        dispatch_path: Path,
        operation_path: Path,
    ) -> tuple[Path, Path]:
        calls.append(
            ("export", actual_report, dispatch_path, operation_path)
        )
        return dispatch_path, operation_path

    monkeypatch.setattr(cli, "run_optimization", run_optimization)
    monkeypatch.setattr(cli, "write_report_csv", write_report_csv)
    monkeypatch.setattr(
        cli.logging,
        "basicConfig",
        lambda **kwargs: log_settings.append(tuple(kwargs.items())),
    )

    result = cli.main(["--input", str(input_path)])

    assert result == 0
    assert dict(log_settings[0]) == {
        "level": cli.logging.INFO,
        "format": "%(levelname)s: %(message)s",
    }
    assert calls == [
        ("optimize", input_path, None, 1000, None, None),
        (
            "export",
            report,
            Path("results/dispatch.csv"),
            Path("results/operation.csv"),
        ),
    ]


def test_optimize_command_forwards_custom_paths_and_tolerance(
    monkeypatch, tmp_path: Path
) -> None:
    input_path = tmp_path / "market-data.xlsx"
    dispatch_path = tmp_path / "market" / "custom-dispatch.csv"
    operation_path = tmp_path / "battery" / "custom-operation.csv"
    calls: list[tuple[object, ...]] = []
    log_settings: list[tuple[object, ...]] = []

    def run_optimization(
        file_path: Path,
        config: object,
        tolerance_millis: int,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> object:
        calls.append(
            (file_path, config, tolerance_millis, start_time, end_time)
        )
        return _report()

    def write_report_csv(
        _report: object,
        actual_dispatch_path: Path,
        actual_operation_path: Path,
    ) -> tuple[Path, Path]:
        calls.append((actual_dispatch_path, actual_operation_path))
        return actual_dispatch_path, actual_operation_path

    monkeypatch.setattr(cli, "run_optimization", run_optimization)
    monkeypatch.setattr(cli, "write_report_csv", write_report_csv)
    monkeypatch.setattr(
        cli.logging,
        "basicConfig",
        lambda **kwargs: log_settings.append(tuple(kwargs.items())),
    )

    result = cli.main(
        [
            "-i",
            str(input_path),
            "-d",
            str(dispatch_path),
            "-o",
            str(operation_path),
            "-t",
            "250",
            "-v",
            "DEBUG",
            "-s",
            "2025-01-01T01:00:00",
            "-e",
            "2025-01-01T02:00:00",
        ]
    )

    assert result == 0
    assert dict(log_settings[0])["level"] == cli.logging.DEBUG
    assert calls == [
        (
            input_path,
            None,
            250,
            datetime(2025, 1, 1, 1),
            datetime(2025, 1, 1, 2),
        ),
        (dispatch_path, operation_path),
    ]


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError("input workbook not found"),
        ValueError("selected period is invalid"),
        RuntimeError("solver is unavailable"),
    ],
)
def test_reports_expected_errors_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    def fail_optimization(*_args: object, **_kwargs: object) -> object:
        raise error

    monkeypatch.setattr(cli, "run_optimization", fail_optimization)
    monkeypatch.setattr(cli.logging, "basicConfig", lambda **_: None)

    result = cli.main(["--input", "markets.xlsx"])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err == f"Error: {error}\n"
    assert "Traceback" not in captured.err


def test_help_explains_time_window_behavior(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["--help"])

    assert raised.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "start is inclusive, end is exclusive" in help_text
    assert "Bounds outside data coverage are clipped" in help_text
    assert "align with boundaries shared by all markets" in help_text
    assert "A window with no overlap is an error" in help_text
