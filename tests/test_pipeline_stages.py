"""Smoke tests confirming every pipeline stage API is importable and present."""

import battery_arbitrage.domain as domain
import battery_arbitrage.optimization as optimization
import battery_arbitrage.parsing as parsing
import battery_arbitrage.reporting as reporting
import battery_arbitrage.time_alignment as time_alignment
import battery_arbitrage.validation as validation


def test_domain_module_has_expected_symbols() -> None:
    assert hasattr(domain, "MarketData")
    assert hasattr(domain, "Timeline")
    assert hasattr(domain, "BatteryConfig")
    assert hasattr(domain, "OptimizationResult")
    assert hasattr(domain, "DispatchReport")


def test_parsing_api_exists() -> None:
    assert callable(parsing.parse_market_data)


def test_validation_api_exists() -> None:
    assert callable(validation.validate_market_data)


def test_time_alignment_api_exists() -> None:
    assert callable(time_alignment.align_market_data)


def test_optimization_api_exists() -> None:
    assert callable(optimization.optimize_battery)


def test_reporting_api_exists() -> None:
    assert callable(reporting.build_report)
