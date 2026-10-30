from pathlib import Path

from battery_arbitrage.domain import BatteryConfig, DispatchReport


def run_optimization(
    file_path: str | Path,
    config: BatteryConfig | None = None,
    tolerance_millis: int = 1000,
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
    raise NotImplementedError("run_optimization is not implemented yet")
