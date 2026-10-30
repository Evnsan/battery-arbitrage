"""Smoke tests confirming every pipeline stage API is importable and present."""

from battery_arbitrage import (
    domain,
    optimization,
    parsing,
    reporting,
    time_alignment,
    validation,
)


def test_domain_module_has_expected_symbols():
    assert hasattr(domain, "MarketData")
    assert hasattr(domain, "Timeline")
    assert hasattr(domain, "BatteryConfig")
    assert hasattr(domain, "OptimizationResult")
    assert hasattr(domain, "DispatchReport")


def test_parsing_api_exists():
    assert callable(parsing.parse_market_data)


def test_validation_api_exists():
    assert callable(validation.validate_market_data)


def test_time_alignment_api_exists():
    assert callable(time_alignment.align_market_data)


def test_optimization_api_exists():
    assert callable(optimization.optimize_battery)


def test_reporting_api_exists():
    assert callable(reporting.build_report)
