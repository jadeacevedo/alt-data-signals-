"""
Unit tests for the data quality checks. Run with: pytest tests/

These are intentionally simple, constructed DataFrames rather than pipeline
output - unit tests for data quality logic should be deterministic and not
depend on the (randomized) synthetic data generator.
"""

import pandas as pd
import pytest

import config
from src.quality_checks import (
    check_completeness,
    check_duplicates,
    check_outliers,
    check_timeliness_gaps,
)


@pytest.fixture(autouse=True)
def small_date_range(monkeypatch):
    """Use a short date range so completeness/gap tests run fast and are easy to reason about."""
    monkeypatch.setattr(config, "START_DATE", "2024-01-01")
    monkeypatch.setattr(config, "END_DATE", "2024-03-31")


def test_check_duplicates_flags_exact_duplicates():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-07", "2024-01-07", "2024-01-14"]),
        "ticker": ["TEST", "TEST", "TEST"],
        "search_interest": [50.0, 50.0, 55.0],
    })
    result = check_duplicates(df, "TEST")
    assert result.passed is False
    assert result.metric_value == 1


def test_check_duplicates_passes_with_no_duplicates():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-07", "2024-01-14"]),
        "ticker": ["TEST", "TEST"],
        "search_interest": [50.0, 55.0],
    })
    result = check_duplicates(df, "TEST")
    assert result.passed is True
    assert result.metric_value == 0


def test_check_outliers_flags_extreme_value():
    values = [50.0] * 20 + [1000.0]  # one wildly extreme value
    dates = pd.date_range("2024-01-01", periods=len(values), freq="W-SUN")
    df = pd.DataFrame({"date": dates, "ticker": "TEST", "search_interest": values})
    result = check_outliers(df, "TEST")
    assert result.passed is False
    assert result.metric_value >= 1


def test_check_outliers_passes_with_stable_data():
    values = [50.0, 51.0, 49.0, 52.0, 48.0]
    dates = pd.date_range("2024-01-01", periods=len(values), freq="W-SUN")
    df = pd.DataFrame({"date": dates, "ticker": "TEST", "search_interest": values})
    result = check_outliers(df, "TEST")
    assert result.passed is True


def test_check_timeliness_gaps_flags_large_gap():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-03-01"]),  # ~60 day gap
        "ticker": ["TEST", "TEST"],
        "search_interest": [50.0, 55.0],
    })
    result = check_timeliness_gaps(df, "TEST")
    assert result.passed is False


def test_check_completeness_flags_missing_weeks():
    # Only provide 2 weeks out of the full quarter's worth of expected weeks
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-07", "2024-01-14"]),
        "ticker": ["TEST", "TEST"],
        "search_interest": [50.0, 55.0],
    })
    result = check_completeness(df, "TEST")
    assert result.passed is False
    assert result.metric_value > config.MAX_NULL_RATE
