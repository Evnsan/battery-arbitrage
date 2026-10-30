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
class OptimizationResult:
    timestamps: tuple[datetime, ...]
    market_names: tuple[MarketName, ...]
    timestep: timedelta
    charge_mw: PowerByMarketAndTime
    discharge_mw: PowerByMarketAndTime
    energy_mwh: EnergyByTime
    total_profit_gbp: float


@dataclass(frozen=True)
class BatteryConfig:
    max_charge_mw: float
    max_discharge_mw: float
    storage_capacity_mwh: float
    initial_energy_mwh: float


@dataclass(frozen=True)
class DispatchRow:
    timestamp: datetime
    market_name: MarketName
    price: float
    charge_mw: float
    discharge_mw: float


@dataclass(frozen=True)
class DispatchReport:
    rows: tuple[DispatchRow, ...]
    total_profit_gbp: float
