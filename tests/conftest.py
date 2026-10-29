"""Shared pytest fixtures for the battery arbitrage project."""

from datetime import timedelta

import pytest

from battery_arbitrage.domain import BatteryConfig


@pytest.fixture
def battery_config() -> BatteryConfig:
    """Standard battery configuration used across the project."""
    return BatteryConfig(
        max_charge_mw=5.0,
        max_discharge_mw=5.0,
        storage_capacity_mwh=10.0,
        initial_energy_mwh=2.0,
    )


@pytest.fixture
def common_period() -> timedelta:
    """The common half-hourly physical timeline interval."""
    return timedelta(minutes=30)
