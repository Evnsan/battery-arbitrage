import logging

from battery_arbitrage.domain import (
    DispatchReport,
    DispatchRow,
    OperationRow,
    OptimizationResult,
    Timeline,
)

logger = logging.getLogger(__name__)


def build_report(
    solution: OptimizationResult,
    timeline: Timeline,
) -> DispatchReport:
    """Build deterministic market dispatch and battery operation rows."""
    logger.info(
        "Building report for %d timesteps across %d markets",
        len(solution.timestamps),
        len(solution.market_names),
    )

    timestep_hours = timeline.common_period.total_seconds() / 3600.0
    timestamps = sorted(solution.timestamps)
    market_names = sorted(solution.market_names)

    dispatch_rows = tuple(
        DispatchRow(
            timestamp=timestamp,
            market_name=market_name,
            price=timeline.prices[timestamp][market_name],
            charge_mw=solution.charge_mw[(market_name, timestamp)],
            discharge_mw=solution.discharge_mw[(market_name, timestamp)],
            cash_flow_gbp=(
                solution.discharge_mw[(market_name, timestamp)]
                - solution.charge_mw[(market_name, timestamp)]
            )
            * timeline.prices[timestamp][market_name]
            * timestep_hours,
        )
        for timestamp in timestamps
        for market_name in market_names
    )

    totals_by_timestamp = {
        timestamp: [0.0, 0.0, 0.0] for timestamp in timestamps
    }
    for row in dispatch_rows:
        totals = totals_by_timestamp[row.timestamp]
        totals[0] += row.charge_mw
        totals[1] += row.discharge_mw
        totals[2] += row.cash_flow_gbp

    operation_rows: list[OperationRow] = []
    cumulative_cash_flow_gbp = 0.0
    for timestamp in timestamps:
        charge_mw, discharge_mw, cash_flow_gbp = totals_by_timestamp[timestamp]
        cumulative_cash_flow_gbp += cash_flow_gbp
        operation_rows.append(
            OperationRow(
                timestamp=timestamp,
                charge_mw=charge_mw,
                discharge_mw=discharge_mw,
                energy_mwh=solution.energy_mwh[timestamp],
                cash_flow_gbp=cash_flow_gbp,
                cumulative_cash_flow_gbp=cumulative_cash_flow_gbp,
            )
        )

    report = DispatchReport(
        dispatch_rows=dispatch_rows,
        operation_rows=tuple(operation_rows),
        total_profit_gbp=solution.total_profit_gbp,
    )
    logger.info(
        "Report built with %d dispatch rows, %d operation rows, "
        "and profit £%.2f",
        len(report.dispatch_rows),
        len(report.operation_rows),
        report.total_profit_gbp,
    )
    return report
