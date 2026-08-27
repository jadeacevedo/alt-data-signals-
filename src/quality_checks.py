"""
Automated data quality checks (bronze -> silver gate).

These run against the raw ingested data BEFORE any cleaning/signal work
happens. The goal is to catch the kinds of issues that quietly corrupt a
signal: missing weeks, duplicate records, stale/late data, and outliers that
might be vendor errors rather than real spikes.

Every check returns a structured result (not just pass/fail) so the quality
report can be handed to an analyst/PM as documentation, not just a log line.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

import config


@dataclass
class CheckResult:
    check_name: str
    ticker: str
    passed: bool
    detail: str
    metric_value: float | None = None


def check_completeness(df: pd.DataFrame, ticker: str) -> CheckResult:
    """Flag if too many expected weekly observations are missing."""
    ticker_df = df[df["ticker"] == ticker]
    expected_weeks = pd.date_range(config.START_DATE, config.END_DATE, freq="W-SUN")
    observed_weeks = pd.to_datetime(ticker_df["date"]).unique()
    missing = len(set(expected_weeks) - set(observed_weeks))
    null_rate = missing / len(expected_weeks)

    passed = bool(null_rate <= config.MAX_NULL_RATE)
    return CheckResult(
        check_name="completeness",
        ticker=ticker,
        passed=passed,
        detail=f"{missing} of {len(expected_weeks)} expected weekly observations missing "
               f"({null_rate:.1%}), threshold is {config.MAX_NULL_RATE:.1%}",
        metric_value=round(null_rate, 4),
    )


def check_timeliness_gaps(df: pd.DataFrame, ticker: str) -> CheckResult:
    """Flag if any single gap between consecutive observations is suspiciously large."""
    ticker_df = df[df["ticker"] == ticker].sort_values("date")
    dates = pd.to_datetime(ticker_df["date"])
    gaps = dates.diff().dt.days.dropna()
    max_gap = gaps.max() if not gaps.empty else 0

    passed = bool(max_gap <= config.MAX_GAP_DAYS)
    return CheckResult(
        check_name="timeliness_gaps",
        ticker=ticker,
        passed=passed,
        detail=f"Largest gap between observations is {max_gap} days "
               f"(threshold {config.MAX_GAP_DAYS} days)",
        metric_value=float(max_gap),
    )


def check_duplicates(df: pd.DataFrame, ticker: str) -> CheckResult:
    """Flag exact duplicate (date, ticker) records - a common vendor-feed bug."""
    ticker_df = df[df["ticker"] == ticker]
    dup_count = ticker_df.duplicated(subset=["date", "ticker"]).sum()

    passed = bool(dup_count == 0)
    return CheckResult(
        check_name="duplicates",
        ticker=ticker,
        passed=passed,
        detail=f"{dup_count} duplicate (date, ticker) records found",
        metric_value=float(dup_count),
    )


def check_outliers(df: pd.DataFrame, ticker: str) -> CheckResult:
    """
    Flag observations more than OUTLIER_Z_THRESHOLD std devs from the mean.
    This doesn't auto-remove them - a real spike (e.g. a viral event) might be
    a legitimate, important signal, not an error. It just flags them for
    analyst review, which is the right posture for alt data.
    """
    ticker_df = df[df["ticker"] == ticker]
    values = ticker_df["search_interest"].astype(float)
    z_scores = (values - values.mean()) / values.std(ddof=0)
    outliers = ticker_df[np.abs(z_scores) > config.OUTLIER_Z_THRESHOLD]

    passed = bool(len(outliers) == 0)
    return CheckResult(
        check_name="outliers",
        ticker=ticker,
        passed=passed,
        detail=f"{len(outliers)} observations beyond {config.OUTLIER_Z_THRESHOLD} std devs "
               f"(flagged for review, not auto-removed)",
        metric_value=float(len(outliers)),
    )


def check_schema(df: pd.DataFrame) -> CheckResult:
    """Validate raw data matches the expected schema before anything downstream touches it."""
    from src.ingest import EXPECTED_SCHEMA

    missing_cols = set(EXPECTED_SCHEMA.keys()) - set(df.columns)
    passed = len(missing_cols) == 0
    return CheckResult(
        check_name="schema",
        ticker="ALL",
        passed=passed,
        detail=f"Missing expected columns: {missing_cols}" if missing_cols else "Schema OK",
    )


def run_all_checks(df: pd.DataFrame) -> list[CheckResult]:
    """Run the full quality check suite across every ticker in the data."""
    results = [check_schema(df)]
    for ticker in df["ticker"].unique():
        results.append(check_completeness(df, ticker))
        results.append(check_timeliness_gaps(df, ticker))
        results.append(check_duplicates(df, ticker))
        results.append(check_outliers(df, ticker))
    return results


def write_quality_report(results: list[CheckResult]) -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    payload = [asdict(r) for r in results]
    with open(config.QUALITY_REPORT_PATH, "w") as f:
        json.dump(payload, f, indent=2)


def summarize(results: list[CheckResult]) -> str:
    failed = [r for r in results if not r.passed]
    lines = [f"Data quality checks: {len(results) - len(failed)}/{len(results)} passed."]
    for r in failed:
        lines.append(f"  [FAILED] {r.check_name} ({r.ticker}): {r.detail}")
    return "\n".join(lines)


if __name__ == "__main__":
    raw = pd.read_csv(config.RAW_TRENDS_PATH, parse_dates=["date"])
    results = run_all_checks(raw)
    write_quality_report(results)
    print(summarize(results))
