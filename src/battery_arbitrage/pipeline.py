import logging
from datetime import datetime
from pathlib import Path

from battery_arbitrage.domain import BatteryConfig, DispatchReport
from battery_arbitrage.optimization import optimize_battery
from battery_arbitrage.parsing import parse_market_data
from battery_arbitrage.reporting import build_report
from battery_arbitrage.time_alignment import align_market_data
from battery_arbitrage.time_filter import select_timeline_period
from battery_arbitrage.validation import validate_market_data

logger = logging.getLogger(__name__)


def run_optimization(
    file_path: str | Path,
    config: BatteryConfig | None = None,
    tolerance_millis: int = 1000,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> DispatchReport:
    """Run the market-data-to-dispatch-report optimization pipeline.

    The pipeline parses and validates market data, aligns markets to a common
    timeline, optimizes battery dispatch, and builds a dispatch report.

    Args:
        file_path: Path to the Excel workbook containing market prices.
        config: Battery configuration. Defaults to the standard configuration.
        tolerance_millis: Maximum timestamp deviation allowed during validation
            and alignment, in milliseconds.

    Returns:
        DispatchReport containing dispatch rows and total profit.

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If market data is invalid or markets cannot be aligned.
        RuntimeError: If optimization fails or the solver is unavailable.
    """

    logger.info("Starting optimization pipeline for %s", file_path)

    market_data = parse_market_data(file_path)
    logger.info("Parsed market data")

    market_intervals = validate_market_data(market_data, tolerance_millis)
    logger.info("Validated market data")

    timeline = align_market_data(
        market_data, market_intervals, tolerance_millis
    )
    logger.info("Aligned market data to the physical timeline")

    if start_time is not None or end_time is not None:
        timeline = select_timeline_period(timeline, start_time, end_time)
        logger.info("Selected requested optimization period")

    logger.info("Optimizing battery dispatch")
    solution = optimize_battery(timeline, config)
    logger.info("Optimization completed")

    report = build_report(solution, timeline)
    logger.info("Built optimization report")
    return report
