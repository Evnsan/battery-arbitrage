import csv
import json
from datetime import datetime
from pathlib import Path

from battery_arbitrage.csv_export import write_report_csv
from battery_arbitrage.domain import (
    DispatchReport,
    DispatchRow,
    OperationRow,
)


def test_writes_dispatch_and_operation_reports(tmp_path: Path) -> None:
    timestamp = datetime(2025, 1, 1, 0, 30)
    report = DispatchReport(
        dispatch_rows=(
            DispatchRow(
                timestamp=timestamp,
                market_name="Market A",
                price=50.0,
                charge_mw=0.0,
                discharge_mw=2.0,
                cash_flow_gbp=50.0,
            ),
        ),
        operation_rows=(
            OperationRow(
                timestamp=timestamp,
                charge_mw=0.0,
                discharge_mw=2.0,
                energy_mwh=1.0,
                cash_flow_gbp=50.0,
                cumulative_cash_flow_gbp=50.0,
            ),
        ),
        total_profit_gbp=50.0,
    )

    output_directory = tmp_path / "nested" / "reports"
    dispatch_path, operation_path = write_report_csv(
        report, output_directory
    )

    assert dispatch_path == output_directory / "dispatch.csv"
    assert operation_path == output_directory / "operation.csv"
    assert dispatch_path.exists()
    assert operation_path.exists()
    with dispatch_path.open(newline="", encoding="utf-8") as dispatch_file:
        dispatch_rows = list(csv.DictReader(dispatch_file))
    with operation_path.open(newline="", encoding="utf-8") as operation_file:
        operation_rows = list(csv.DictReader(operation_file))

    assert dispatch_rows == [
        {
            "timestamp": "2025-01-01T00:30:00",
            "market_name": "Market A",
            "price_gbp_per_mwh": "50.0",
            "charge_mw": "0.0",
            "discharge_mw": "2.0",
            "cash_flow_gbp": "50.0",
        }
    ]
    assert operation_rows == [
        {
            "timestamp": "2025-01-01T00:30:00",
            "charge_mw": "0.0",
            "discharge_mw": "2.0",
            "energy_start_mwh": "1.0",
            "cash_flow_gbp": "50.0",
            "cumulative_cash_flow_gbp": "50.0",
        }
    ]
    metadata = json.loads(
        (output_directory / "metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["total_profit_gbp"] == 50.0
    assert metadata["modeled_period_start_inclusive"] is None


def test_writes_headers_for_empty_reports(tmp_path: Path) -> None:
    report = DispatchReport(
        dispatch_rows=(), operation_rows=(), total_profit_gbp=0.0
    )

    dispatch_path, operation_path = write_report_csv(report, tmp_path)

    with dispatch_path.open(newline="", encoding="utf-8") as dispatch_file:
        assert next(csv.reader(dispatch_file)) == [
            "timestamp",
            "market_name",
            "price_gbp_per_mwh",
            "charge_mw",
            "discharge_mw",
            "cash_flow_gbp",
        ]
    with operation_path.open(newline="", encoding="utf-8") as operation_file:
        assert next(csv.reader(operation_file)) == [
            "timestamp",
            "charge_mw",
            "discharge_mw",
            "energy_start_mwh",
            "cash_flow_gbp",
            "cumulative_cash_flow_gbp",
        ]
    assert (tmp_path / "metadata.json").exists()
