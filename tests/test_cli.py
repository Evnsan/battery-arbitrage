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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_path = tmp_path / "market-data.xlsx"
    report = _report()
    calls: list[tuple[object, ...]] = []
    log_settings: list[dict[str, object]] = []

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
        output_directory: Path,
    ) -> tuple[Path, Path]:
        calls.append(("export", actual_report, output_directory))
        return (
            output_directory / "dispatch.csv",
            output_directory / "operation.csv",
        )

    monkeypatch.setattr(cli, "run_optimization", run_optimization)
    monkeypatch.setattr(cli, "write_report_csv", write_report_csv)
    monkeypatch.setattr(
        cli.logging,
        "basicConfig",
        lambda **kwargs: log_settings.append(kwargs),
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
            Path("results/market-data_full"),
        ),
    ]


def test_optimize_command_forwards_output_directory_and_tolerance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_path = tmp_path / "market-data.xlsx"
    output_directory = tmp_path / "custom-results"
    calls: list[tuple[object, ...]] = []
    log_settings: list[dict[str, object]] = []

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
        actual_output_directory: Path,
    ) -> tuple[Path, Path]:
        calls.append((actual_output_directory,))
        return (
            actual_output_directory / "dispatch.csv",
            actual_output_directory / "operation.csv",
        )

    monkeypatch.setattr(cli, "run_optimization", run_optimization)
    monkeypatch.setattr(cli, "write_report_csv", write_report_csv)
    monkeypatch.setattr(
        cli.logging,
        "basicConfig",
        lambda **kwargs: log_settings.append(kwargs),
    )

    result = cli.main(
        [
            "-i",
            str(input_path),
            "-d",
            str(output_directory),
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
        (output_directory,),
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
