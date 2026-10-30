import csv
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

    dispatch_target = tmp_path / "nested" / "market" / "dispatch-data.csv"
    operation_target = tmp_path / "summary" / "battery-operation.csv"
    dispatch_path, operation_path = write_report_csv(
        report, dispatch_target, operation_target
    )

    assert dispatch_path == dispatch_target
    assert operation_path == operation_target
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
            "energy_mwh": "1.0",
            "cash_flow_gbp": "50.0",
            "cumulative_cash_flow_gbp": "50.0",
        }
    ]


def test_writes_headers_for_empty_reports(tmp_path: Path) -> None:
    report = DispatchReport(
        dispatch_rows=(), operation_rows=(), total_profit_gbp=0.0
    )

    dispatch_path, operation_path = write_report_csv(
        report,
        tmp_path / "empty-dispatch.csv",
        tmp_path / "empty-operation.csv",
    )

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
            "energy_mwh",
            "cash_flow_gbp",
            "cumulative_cash_flow_gbp",
        ]
