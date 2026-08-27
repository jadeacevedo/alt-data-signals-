"""
Signal validation and backtesting.

This is the "does the alt data actually predict anything" step. Discipline
here matters more than the correlation number itself:

- Uses only PRIOR-quarter search interest to predict THIS quarter's revenue
  growth (no look-ahead bias - you'd never have the current quarter's full
  search data before the quarter closes).
- Splits into an in-sample fit period and an out-of-sample holdout, since an
  in-sample-only correlation is close to meaningless for a real trading
  decision.
- Reports sample size alongside every statistic, and refuses to call a result
  "reliable" below a minimum sample size (config.MIN_QUARTERS_FOR_BACKTEST) -
  small-sample correlations in alt data are one of the most common ways
  analysts fool themselves.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy import stats

import config


@dataclass
class SignalResult:
    ticker: str
    n_quarters: int
    in_sample_corr: float | None
    in_sample_pvalue: float | None
    out_of_sample_corr: float | None
    out_of_sample_pvalue: float | None
    reliable: bool
    caveats: list[str]


def _correlate(x: pd.Series, y: pd.Series) -> tuple[float | None, float | None]:
    paired = pd.concat([x, y], axis=1).dropna()
    if len(paired) < 3:
        return None, None
    r, p = stats.pearsonr(paired.iloc[:, 0], paired.iloc[:, 1])
    return round(float(r), 4), round(float(p), 4)


def evaluate_ticker(features: pd.DataFrame, ticker: str) -> SignalResult:
    df = features[features["ticker"] == ticker].dropna(
        subset=["avg_search_interest_prior_q", "revenue_qoq_growth"]
    ).reset_index(drop=True)

    n = len(df)
    caveats = []

    if n == 0:
        return SignalResult(ticker, 0, None, None, None, None, False,
                             ["No overlapping data between search interest and revenue."])

    split_idx = int(n * 0.7)
    in_sample = df.iloc[:split_idx]
    out_of_sample = df.iloc[split_idx:]

    in_r, in_p = _correlate(in_sample["avg_search_interest_prior_q"], in_sample["revenue_qoq_growth"])
    out_r, out_p = _correlate(out_of_sample["avg_search_interest_prior_q"], out_of_sample["revenue_qoq_growth"])

    reliable = n >= config.MIN_QUARTERS_FOR_BACKTEST

    if not reliable:
        caveats.append(
            f"Only {n} quarters of overlapping data - below the "
            f"{config.MIN_QUARTERS_FOR_BACKTEST}-quarter minimum this pipeline treats as "
            f"sufficient for a trustworthy correlation. Treat any correlation here as "
            f"exploratory, not decision-grade."
        )
    if out_r is not None and in_r is not None and np.sign(out_r) != np.sign(in_r):
        caveats.append(
            "In-sample and out-of-sample correlation have opposite signs - classic sign of "
            "an unstable or spurious relationship, not a durable signal."
        )
    if len(out_of_sample) < 3:
        caveats.append("Out-of-sample holdout has fewer than 3 quarters - out-of-sample stat is not meaningful.")

    caveats.append(
        "Search interest is a normalized, relative index (0-100), not an absolute volume - "
        "changes in scale/methodology by the data provider could look like a real trend shift."
    )

    return SignalResult(
        ticker=ticker,
        n_quarters=n,
        in_sample_corr=in_r,
        in_sample_pvalue=in_p,
        out_of_sample_corr=out_r,
        out_of_sample_pvalue=out_p,
        reliable=reliable,
        caveats=caveats,
    )


def run_signal_evaluation(features: pd.DataFrame) -> list[SignalResult]:
    return [evaluate_ticker(features, t) for t in features["ticker"].unique()]


def write_signal_report(results: list[SignalResult]) -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.SIGNAL_RESULTS_PATH, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)


def summarize(results: list[SignalResult]) -> str:
    lines = []
    for r in results:
        lines.append(f"\n{r.ticker}: n={r.n_quarters} quarters")
        lines.append(f"  In-sample corr:      {r.in_sample_corr} (p={r.in_sample_pvalue})")
        lines.append(f"  Out-of-sample corr:  {r.out_of_sample_corr} (p={r.out_of_sample_pvalue})")
        lines.append(f"  Reliable enough for decision-grade use: {r.reliable}")
        for c in r.caveats:
            lines.append(f"  - Caveat: {c}")
    return "\n".join(lines)


if __name__ == "__main__":
    features = pd.read_csv(config.QUARTERLY_FEATURES_PATH)
    results = run_signal_evaluation(features)
    write_signal_report(results)
    print(summarize(results))
