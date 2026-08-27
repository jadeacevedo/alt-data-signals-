"""
Ingestion layer (bronze).

Pulls the alt-data proxy (Google Trends search interest) and quarterly revenue
"ground truth" for each ticker in the universe. Raw pulls are written to
data/raw/ untouched - no cleaning happens here. That separation matters: if a
downstream cleaning step turns out to be wrong, you can always re-derive silver
/ gold layers from bronze without re-pulling from the vendor.

Real-world note: in production this is where you'd swap in an actual vendor
SDK (credit card panel API, POS data feed, etc). Everything else in this
pipeline (quality checks, cleaning, signal testing, query layer) is agnostic to
where the raw data came from, as long as it matches EXPECTED_SCHEMA below.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Schema every raw search-interest row must match. Rows that don't conform are
# quarantined rather than silently dropped or allowed to crash the pipeline -
# this is the kind of schema-drift handling a real alt-data vendor feed needs,
# since vendors change field names/formats without much warning.
EXPECTED_SCHEMA = {
    "date": "datetime64[ns]",
    "ticker": "object",
    "search_interest": "float64",
}


def _try_real_pytrends_pull(ticker: str, search_terms: list[str]) -> pd.DataFrame | None:
    """
    Attempt a real Google Trends pull via pytrends. Returns None on any failure
    (network restrictions, rate limits, API changes) so the caller can fall
    back to the synthetic generator. This mirrors how you'd handle a flaky
    real-world vendor API - fail loudly in the logs, but don't take down the
    whole pipeline.
    """
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=360, timeout=(5, 10))
        pytrends.build_payload(
            search_terms, timeframe=f"{config.START_DATE} {config.END_DATE}"
        )
        df = pytrends.interest_over_time()
        if df.empty:
            logger.warning("pytrends returned empty data for %s", ticker)
            return None
        df = df.reset_index().rename(columns={"date": "date", search_terms[0]: "search_interest"})
        df["ticker"] = ticker
        return df[["date", "ticker", "search_interest"]]
    except Exception as exc:  # noqa: BLE001 - any failure should trigger fallback
        logger.warning("Live pytrends pull failed for %s (%s). Falling back to synthetic data.", ticker, exc)
        return None


def _synthetic_search_interest(ticker: str, seed: int) -> pd.DataFrame:
    """
    Documented synthetic fallback so the pipeline is always runnable/testable,
    including in network-restricted environments (e.g. CI, sandboxes).

    IMPORTANT: this is clearly labeled synthetic data, not real search
    interest. It's built to have realistic properties for demoing the
    pipeline: weekly cadence, seasonality, noise, occasional missing weeks,
    and a modest genuine correlation with the (also synthetic) revenue series
    so the signal-testing step has something real to find - exactly the kind
    of caveat you'd document for a PM before they trust a dataset.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range(config.START_DATE, config.END_DATE, freq="W-SUN")

    n = len(dates)
    t = np.arange(n)

    trend = 50 + 0.02 * t                      # slow secular growth
    seasonality = 8 * np.sin(2 * np.pi * t / 52)  # yearly seasonality
    noise = rng.normal(0, 6, n)
    values = trend + seasonality + noise
    values = np.clip(values, 0, 100)

    df = pd.DataFrame({"date": dates, "ticker": ticker, "search_interest": values})

    # Simulate occasional missing weeks (vendor gaps) - drop ~2% of rows at random
    drop_idx = rng.choice(df.index, size=max(1, int(0.02 * n)), replace=False)
    df = df.drop(index=drop_idx).reset_index(drop=True)

    # Simulate a rare bad/duplicate record (data quality issue to catch downstream)
    if n > 10:
        dup_row = df.iloc[[5]].copy()
        df = pd.concat([df, dup_row], ignore_index=True)

    return df


def _synthetic_revenue(ticker: str, search_df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """
    Synthetic quarterly revenue, engineered to have a genuine-but-noisy
    relationship with the search interest series (so the backtest has a real
    signal to find, at a realistic strength - not a toy R^2 of 0.99).
    """
    rng = np.random.default_rng(seed + 1)

    quarters = pd.period_range(config.START_DATE, config.END_DATE, freq="Q")
    search_df = search_df.copy()
    search_df["quarter"] = pd.to_datetime(search_df["date"]).dt.to_period("Q")
    quarterly_search = search_df.groupby("quarter")["search_interest"].mean()

    revenue = []
    for q in quarters:
        base = 500 + 3 * q.ordinal  # secular growth in revenue base
        signal_component = 2.5 * quarterly_search.get(q, quarterly_search.mean())
        noise = rng.normal(0, 40)  # a lot of quarter-to-quarter noise unrelated to search
        revenue.append(base + signal_component + noise)

    return pd.DataFrame({
        "quarter": quarters.astype(str),
        "ticker": ticker,
        "revenue_millions": np.round(revenue, 1),
    })


def ingest_all() -> None:
    """Ingest search-interest and revenue data for every ticker in the universe."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    all_search = []
    all_revenue = []

    for i, (ticker, meta) in enumerate(config.TICKERS.items()):
        logger.info("Ingesting %s (%s)...", ticker, meta["name"])

        df = _try_real_pytrends_pull(ticker, meta["search_terms"])
        if df is None:
            df = _synthetic_search_interest(ticker, seed=42 + i)
            logger.info("Using synthetic search-interest data for %s", ticker)

        all_search.append(df)
        all_revenue.append(_synthetic_revenue(ticker, df, seed=42 + i))

    search_df = pd.concat(all_search, ignore_index=True)
    revenue_df = pd.concat(all_revenue, ignore_index=True)

    search_df.to_csv(config.RAW_TRENDS_PATH, index=False)
    revenue_df.to_csv(config.RAW_REVENUE_PATH, index=False)

    logger.info("Wrote raw search interest -> %s (%d rows)", config.RAW_TRENDS_PATH, len(search_df))
    logger.info("Wrote raw revenue actuals -> %s (%d rows)", config.RAW_REVENUE_PATH, len(revenue_df))


if __name__ == "__main__":
    ingest_all()
