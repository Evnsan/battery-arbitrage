from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeAlias

MarketName: TypeAlias = str

MarketPrices: TypeAlias = dict[datetime, float]
MarketData: TypeAlias = dict[MarketName, MarketPrices]
MarketIntervals: TypeAlias = dict[MarketName, timedelta]
MarketPricesAtTime: TypeAlias = dict[MarketName, float]
TimelinePrices: TypeAlias = dict[datetime, MarketPricesAtTime]


MarketTimestamp: TypeAlias = tuple[MarketName, datetime]
PowerByMarketAndTime: TypeAlias = dict[MarketTimestamp, float]
EnergyByTime: TypeAlias = dict[datetime, float]


@dataclass(frozen=True)
class Timeline:
    prices: TimelinePrices
    common_period: timedelta
    market_intervals: MarketIntervals


@dataclass(frozen=True)
class BatteryConfig:
    max_charge_mw: float
    max_discharge_mw: float
    storage_capacity_mwh: float
    initial_energy_mwh: float


@dataclass(frozen=True)
class OptimizationResult:
    timestamps: tuple[datetime, ...]
    market_names: tuple[MarketName, ...]
    timestep: timedelta
    charge_mw: PowerByMarketAndTime
    discharge_mw: PowerByMarketAndTime
    energy_mwh: EnergyByTime
    total_profit_gbp: float
    battery_config: BatteryConfig | None = None
    solver_relative_mip_gap: float | None = None


@dataclass(frozen=True)
class DispatchRow:
    timestamp: datetime
    market_name: MarketName
    price: float
    charge_mw: float
    discharge_mw: float
    cash_flow_gbp: float


@dataclass(frozen=True)
class OperationRow:
    timestamp: datetime
    charge_mw: float
    discharge_mw: float
    energy_mwh: float
    cash_flow_gbp: float
    cumulative_cash_flow_gbp: float


@dataclass(frozen=True)
class DispatchReport:
    dispatch_rows: tuple[DispatchRow, ...]
    operation_rows: tuple[OperationRow, ...]
    total_profit_gbp: float
    modeled_period_start: datetime | None = None
    modeled_period_end: datetime | None = None
    timestep: timedelta | None = None
    battery_config: BatteryConfig | None = None
    solver_relative_mip_gap: float | None = None
