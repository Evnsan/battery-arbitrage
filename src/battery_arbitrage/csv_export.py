import csv
import json
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
    "energy_start_mwh",
    "cash_flow_gbp",
    "cumulative_cash_flow_gbp",
)


def write_report_csv(
    report: DispatchReport,
    output_directory: str | Path,
) -> tuple[Path, Path]:
    """Write dispatch and operation report rows as CSV files.

    The output directory is created when it does not already exist. Files are
    named ``dispatch.csv`` and ``operation.csv``. Returns their paths, in
    that order.
    """
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    dispatch_path = output_directory / "dispatch.csv"
    operation_path = output_directory / "operation.csv"

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
                "energy_start_mwh": row.energy_mwh,
                "cash_flow_gbp": row.cash_flow_gbp,
                "cumulative_cash_flow_gbp": row.cumulative_cash_flow_gbp,
            }
            for row in report.operation_rows
        )

    metadata = {
        "total_profit_gbp": report.total_profit_gbp,
        "modeled_period_start_inclusive": (
            report.modeled_period_start.isoformat()
            if report.modeled_period_start is not None
            else None
        ),
        "modeled_period_end_exclusive": (
            report.modeled_period_end.isoformat()
            if report.modeled_period_end is not None
            else None
        ),
        "timestep_seconds": (
            report.timestep.total_seconds()
            if report.timestep is not None
            else None
        ),
        "battery": (
            {
                "max_charge_mw": report.battery_config.max_charge_mw,
                "max_discharge_mw": report.battery_config.max_discharge_mw,
                "storage_capacity_mwh": (
                    report.battery_config.storage_capacity_mwh
                ),
                "initial_energy_mwh": (
                    report.battery_config.initial_energy_mwh
                ),
            }
            if report.battery_config is not None
            else None
        ),
        "solver_relative_mip_gap_tolerance": report.solver_relative_mip_gap,
    }
    (output_directory / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    return dispatch_path, operation_path
