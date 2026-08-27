"""
Silver -> gold transformation layer.

Takes raw (bronze) search-interest data that has passed quality checks and
turns it into clean, analysis-ready quarterly features (gold layer) aligned
with revenue actuals. This is where deduplication, gap-handling, and
aggregation live - kept separate from ingestion so re-running cleaning logic
never requires re-pulling from the vendor.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def clean_search_interest(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Silver layer: dedupe, sort, and linearly interpolate small gaps.
    Interpolation is capped - we only fill gaps up to MAX_GAP_DAYS worth of
    missing weeks; anything beyond that is left as a real gap rather than
    fabricating data, and remains visible in the quality report.
    """
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"])

    before = len(df)
    df = df.drop_duplicates(subset=["date", "ticker"]).sort_values(["ticker", "date"])
    removed = before - len(df)
    if removed:
        logger.info("Removed %d duplicate rows during cleaning", removed)

    cleaned_frames = []
    for ticker, group in df.groupby("ticker"):
        group = group.set_index("date").asfreq("W-SUN")
        group["ticker"] = ticker
        max_gap_weeks = config.MAX_GAP_DAYS // 7
        group["search_interest"] = group["search_interest"].interpolate(
            method="linear", limit=max_gap_weeks
        )
        cleaned_frames.append(group.reset_index())

    cleaned = pd.concat(cleaned_frames, ignore_index=True)
    cleaned = cleaned.dropna(subset=["search_interest"])  # drop gaps too large to interpolate
    return cleaned[["date", "ticker", "search_interest"]]


def build_quarterly_features(cleaned: pd.DataFrame, revenue: pd.DataFrame) -> pd.DataFrame:
    """
    Gold layer: aggregate weekly search interest into quarterly features and
    align with revenue actuals. Includes a lagged feature (prior quarter's
    average search interest) since that's what you'd actually have available
    BEFORE a quarter's earnings are reported - this is what makes the later
    backtest honest rather than look-ahead biased.
    """
    cleaned = cleaned.copy()
    cleaned["quarter"] = cleaned["date"].dt.to_period("Q").astype(str)

    quarterly = (
        cleaned.groupby(["ticker", "quarter"])["search_interest"]
        .agg(avg_search_interest="mean", search_interest_volatility="std", n_obs="count")
        .reset_index()
    )

    merged = quarterly.merge(revenue, on=["ticker", "quarter"], how="inner")
    merged = merged.sort_values(["ticker", "quarter"])

    # Lagged (prior-quarter) feature - the only version of the feature that
    # would actually have been available before THIS quarter's revenue print.
    merged["avg_search_interest_prior_q"] = merged.groupby("ticker")["avg_search_interest"].shift(1)
    merged["revenue_qoq_growth"] = merged.groupby("ticker")["revenue_millions"].pct_change()

    return merged


def run_pipeline() -> pd.DataFrame:
    raw = pd.read_csv(config.RAW_TRENDS_PATH, parse_dates=["date"])
    revenue = pd.read_csv(config.RAW_REVENUE_PATH)

    cleaned = clean_search_interest(raw)
    cleaned.to_csv(config.CLEANED_PATH, index=False)
    logger.info("Wrote cleaned search interest -> %s (%d rows)", config.CLEANED_PATH, len(cleaned))

    features = build_quarterly_features(cleaned, revenue)
    features.to_csv(config.QUARTERLY_FEATURES_PATH, index=False)
    logger.info("Wrote quarterly features -> %s (%d rows)", config.QUARTERLY_FEATURES_PATH, len(features))

    return features


if __name__ == "__main__":
    run_pipeline()
