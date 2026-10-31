import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from typing import Any, cast

import pyomo.environ as pyo
from pyomo.opt import SolverStatus, TerminationCondition

from battery_arbitrage.domain import BatteryConfig, OptimizationResult, Timeline

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _HighsConfig:
    time_limit_seconds: float = 300.0
    relative_mip_gap: float = 0.02
    print_output: bool = True


_HIGHS_CONFIG = _HighsConfig()

_DEFAULT_BATTERY_CONFIG = BatteryConfig(
    max_charge_mw=5.0,
    max_discharge_mw=5.0,
    storage_capacity_mwh=10.0,
    initial_energy_mwh=2.0,
)


def optimize_battery(
    timeline: Timeline,
    config: BatteryConfig | None = None,
) -> OptimizationResult:
    """Maximize battery arbitrage profit across multiple markets.

    Args:
        timeline:
            Timeline instance containing aligned market prices, common
            interval, and per-market intervals.
        config:
            BatteryConfig instance. Defaults to the standard configuration.

    Returns:
        OptimizationResult containing the solved model and schedule. The
        charge and discharge maps are dense: every market and timestamp pair
        has an entry, including zero-valued entries. ``energy_mwh[t]`` is the
        stored energy at the start of timestep ``t``, so its first value equals
        the initial energy. ``total_profit_gbp`` is
        ``sum((discharge - charge) * price * common_period_hours)`` over all
        markets and timestamps.

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
    if config is None:
        config = _DEFAULT_BATTERY_CONFIG

    _validate_config(config)
    timestamps, market_names, steps_per_interval = _prepare_timeline(timeline)
    model = _build_model(
        timeline,
        config,
        timestamps,
        market_names,
        steps_per_interval,
    )
    _solve(model)

    return _build_result(
        model,
        timeline,
        timestamps,
        market_names,
        steps_per_interval,
    )


def _validate_config(config: BatteryConfig) -> None:
    if config.max_charge_mw < 0:
        raise ValueError("Maximum charging power cannot be negative")
    if config.max_discharge_mw < 0:
        raise ValueError("Maximum discharging power cannot be negative")
    if config.storage_capacity_mwh < 0:
        raise ValueError("Storage capacity cannot be negative")
    if not 0 <= config.initial_energy_mwh <= config.storage_capacity_mwh:
        raise ValueError(
            "Initial energy must be between zero and storage capacity"
        )


def _prepare_timeline(
    timeline: Timeline,
) -> tuple[tuple[datetime, ...], tuple[str, ...], dict[str, int]]:
    if not timeline.prices:
        raise ValueError("Timeline has no prices")
    if timeline.common_period <= timedelta(0):
        raise ValueError("Timeline common period must be positive")

    timestamps = tuple(sorted(timeline.prices))
    for previous, current in pairwise(timestamps):
        if current - previous != timeline.common_period:
            raise ValueError(
                "Timeline timestamps must be spaced by the common period"
            )

    market_names = tuple(sorted(timeline.prices[timestamps[0]]))
    if not market_names:
        raise ValueError("Timeline has no markets")

    market_set = set(market_names)
    for timestamp in timestamps:
        if set(timeline.prices[timestamp]) != market_set:
            raise ValueError(
                "Timeline prices must contain the same markets at every "
                "timestamp"
            )

    if set(timeline.market_intervals) != market_set:
        raise ValueError(
            "Timeline market intervals must match the market names"
        )

    steps_per_interval: dict[str, int] = {}
    for market_name in market_names:
        interval = timeline.market_intervals[market_name]
        if interval <= timedelta(0) or interval % timeline.common_period:
            raise ValueError(
                f"Market '{market_name}' interval must be a positive "
                "multiple of the common period"
            )
        steps = interval // timeline.common_period
        if len(timestamps) % steps:
            raise ValueError(
                f"Timeline does not cover complete '{market_name}' intervals"
            )
        steps_per_interval[market_name] = steps

    return timestamps, market_names, steps_per_interval


def _build_model(
    timeline: Timeline,
    config: BatteryConfig,
    timestamps: tuple[datetime, ...],
    market_names: tuple[str, ...],
    steps_per_interval: dict[str, int],
) -> Any:
    step_count = len(timestamps)
    delta_hours = timeline.common_period.total_seconds() / 3600.0
    market_interval_pairs = [
        (market_name, interval_index)
        for market_name in market_names
        for interval_index in range(
            step_count // steps_per_interval[market_name]
        )
    ]

    def interval_index(market_name: str, step: int) -> int:
        return step // steps_per_interval[market_name]

    def aggregate_charge(model: Any, step: int) -> Any:
        return pyo.quicksum(
            model.charge[market_name, interval_index(market_name, step)]
            for market_name in market_names
        )

    def aggregate_discharge(model: Any, step: int) -> Any:
        return pyo.quicksum(
            model.discharge[market_name, interval_index(market_name, step)]
            for market_name in market_names
        )

    model: Any = pyo.ConcreteModel()
    model.charge = pyo.Var(
        market_interval_pairs,
        domain=pyo.NonNegativeReals,
        bounds=(0.0, config.max_charge_mw),
    )
    model.discharge = pyo.Var(
        market_interval_pairs,
        domain=pyo.NonNegativeReals,
        bounds=(0.0, config.max_discharge_mw),
    )
    model.energy = pyo.Var(
        range(step_count + 1),
        domain=pyo.NonNegativeReals,
        bounds=(0.0, config.storage_capacity_mwh),
    )
    cast(Any, model.energy[0]).fix(config.initial_energy_mwh)
    model.operating_mode = pyo.Var(range(step_count), domain=pyo.Binary)

    def energy_balance_rule(model: Any, step: int) -> Any:
        return (
            model.energy[step + 1]
            == model.energy[step]
            + (aggregate_charge(model, step) - aggregate_discharge(model, step))
            * delta_hours
        )

    def charge_limit_rule(model: Any, step: int) -> Any:
        return aggregate_charge(model, step) <= (
            config.max_charge_mw * model.operating_mode[step]
        )

    def discharge_limit_rule(model: Any, step: int) -> Any:
        return aggregate_discharge(model, step) <= (
            config.max_discharge_mw * (1 - model.operating_mode[step])
        )

    def profit_rule(model: Any) -> Any:
        return pyo.quicksum(
            (
                model.discharge[market_name, interval_index(market_name, step)]
                - model.charge[market_name, interval_index(market_name, step)]
            )
            * timeline.prices[timestamp][market_name]
            * delta_hours
            for market_name in market_names
            for step, timestamp in enumerate(timestamps)
        )

    model.energy_balance = pyo.Constraint(
        range(step_count),
        rule=energy_balance_rule,
    )
    model.charge_limit = pyo.Constraint(
        range(step_count),
        rule=charge_limit_rule,
    )
    model.discharge_limit = pyo.Constraint(
        range(step_count),
        rule=discharge_limit_rule,
    )
    model.profit = pyo.Objective(rule=profit_rule, sense=pyo.maximize)
    return model


def _solve(model: Any) -> None:
    solver = pyo.SolverFactory("highs")

    if not solver.available(exception_flag=False):
        raise RuntimeError("HiGHS solver is not available")

    solver.options["time_limit"] = _HIGHS_CONFIG.time_limit_seconds
    solver.options["mip_rel_gap"] = _HIGHS_CONFIG.relative_mip_gap

    logger.info(
        "Starting HiGHS solve (time limit %.0f seconds, "
        "relative MIP gap %.1f%%)",
        _HIGHS_CONFIG.time_limit_seconds,
        _HIGHS_CONFIG.relative_mip_gap * 100,
    )
    results = solver.solve(model, tee=_HIGHS_CONFIG.print_output)
    termination = results.solver.termination_condition
    logger.info(
        "HiGHS solve finished with termination condition %s", termination
    )
    if termination == TerminationCondition.infeasible:
        raise ValueError("Optimization model is infeasible")
    if (
        results.solver.status != SolverStatus.ok
        or termination != TerminationCondition.optimal
    ):
        raise RuntimeError(
            "Optimization failed with status "
            f"'{results.solver.status}' and termination "
            f"condition '{termination}'"
        )


def _build_result(
    model: Any,
    timeline: Timeline,
    timestamps: tuple[datetime, ...],
    market_names: tuple[str, ...],
    steps_per_interval: dict[str, int],
) -> OptimizationResult:
    delta_hours = timeline.common_period.total_seconds() / 3600.0
    charge_mw: dict[tuple[str, datetime], float] = {}
    discharge_mw: dict[tuple[str, datetime], float] = {}

    for market_name in market_names:
        for step, timestamp in enumerate(timestamps):
            interval_index = step // steps_per_interval[market_name]
            charge_mw[(market_name, timestamp)] = cast(
                float,
                pyo.value(model.charge[market_name, interval_index]),
            )
            discharge_mw[(market_name, timestamp)] = cast(
                float,
                pyo.value(model.discharge[market_name, interval_index]),
            )

    energy_mwh = {
        timestamp: cast(float, pyo.value(model.energy[step]))
        for step, timestamp in enumerate(timestamps)
    }
    total_profit_gbp = sum(
        (
            discharge_mw[(market_name, timestamp)]
            - charge_mw[(market_name, timestamp)]
        )
        * timeline.prices[timestamp][market_name]
        * delta_hours
        for market_name in market_names
        for timestamp in timestamps
    )

    return OptimizationResult(
        timestamps=timestamps,
        market_names=market_names,
        timestep=timeline.common_period,
        charge_mw=charge_mw,
        discharge_mw=discharge_mw,
        energy_mwh=energy_mwh,
        total_profit_gbp=total_profit_gbp,
    )
