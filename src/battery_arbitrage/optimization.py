from battery_arbitrage.domain import BatteryConfig, OptimizationResult, Timeline


def optimize_battery(
    timeline: Timeline,
    config: BatteryConfig | None = None,
) -> OptimizationResult:
    """Maximize battery arbitrage profit across multiple markets.

    Args:
        timeline:
            Timeline instance containing aligned market prices and common interval.
        config:
            BatteryConfig instance. Defaults to the standard configuration.

    Returns:
        OptimizationResult containing the solved model and schedule.

    Raises:
        ValueError: If inputs are invalid or the model is infeasible.
        RuntimeError: If the solver is unavailable or optimization fails.

    Assumptions:
        - All market prices are known over the optimization horizon.
        - Charging and discharging efficiency are both 100%.
        - The final battery energy is unconstrained.
        - Market commitments remain constant throughout each market interval.
        - The battery cannot charge and discharge simultaneously.
    """

    raise NotImplementedError("optimize_battery is not implemented yet")
