import csv
from pathlib import Path

from battery_arbitrage.domain import DispatchReport

DISPATCH_FIELDS = (
    "timestamp",
    "market_name",
    "price_gbp_per_mwh",
    "charge_mw",
    "discharge_mw",
    "cash_flow_gbp",
)
OPERATION_FIELDS = (
    "timestamp",
    "charge_mw",
    "discharge_mw",
    "energy_mwh",
    "cash_flow_gbp",
    "cumulative_cash_flow_gbp",
)


def write_report_csv(
    report: DispatchReport,
    dispatch_path: str | Path,
    operation_path: str | Path,
) -> tuple[Path, Path]:
    """Write dispatch and operation report rows as CSV files.

    Parent directories are created when they do not already exist. Returns
    the dispatch and operation file paths, in that order.
    """
    dispatch_path = Path(dispatch_path)
    operation_path = Path(operation_path)
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    operation_path.parent.mkdir(parents=True, exist_ok=True)

    with dispatch_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=DISPATCH_FIELDS)
        writer.writeheader()
        writer.writerows(
            {
                "timestamp": row.timestamp.isoformat(),
                "market_name": row.market_name,
                "price_gbp_per_mwh": row.price,
                "charge_mw": row.charge_mw,
                "discharge_mw": row.discharge_mw,
                "cash_flow_gbp": row.cash_flow_gbp,
            }
            for row in report.dispatch_rows
        )

    with operation_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OPERATION_FIELDS)
        writer.writeheader()
        writer.writerows(
            {
                "timestamp": row.timestamp.isoformat(),
                "charge_mw": row.charge_mw,
                "discharge_mw": row.discharge_mw,
                "energy_mwh": row.energy_mwh,
                "cash_flow_gbp": row.cash_flow_gbp,
                "cumulative_cash_flow_gbp": row.cumulative_cash_flow_gbp,
            }
            for row in report.operation_rows
        )

    return dispatch_path, operation_path
