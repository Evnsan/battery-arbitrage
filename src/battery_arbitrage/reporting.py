from battery_arbitrage.domain import (
    DispatchReport,
    OptimizationResult,
    Timeline,
)


def build_report(
    solution: OptimizationResult, timeline: Timeline
) -> DispatchReport:
    """
    Return battery-operation and market-dispatch report rows.
    """
    raise NotImplementedError("build_reports is not implemented yet")
    return DispatchReport(rows=(), total_profit_gbp=0.0)
