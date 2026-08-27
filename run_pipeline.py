"""
Single entrypoint: ingest -> quality check -> clean/build features -> signal
test -> memo. Mirrors the day-to-day loop this role would actually own.

Usage:
    python run_pipeline.py
"""

from __future__ import annotations

import pandas as pd

import config
from src import ingest, pipeline, query_agent, quality_checks, signal


def populate_memo(ticker: str, quality_results, signal_result) -> str:
    template_path = config.MEMO_DIR / "data_quality_memo_template.md"
    template = template_path.read_text()

    ticker_quality = [r for r in quality_results if r.ticker in (ticker, "ALL")]
    failed = [r for r in ticker_quality if not r.passed]

    def fmt(check_name):
        match = next((r for r in ticker_quality if r.check_name == check_name), None)
        return match.detail if match else "N/A"

    caveats_list = "\n".join(f"- {c}" for c in signal_result.caveats) if signal_result.caveats else "- None."

    if signal_result.reliable and signal_result.out_of_sample_corr and abs(signal_result.out_of_sample_corr) > 0.3:
        recommendation = (
            "Signal shows a moderate, out-of-sample-validated relationship. Suitable as a "
            "SUPPORTING input alongside fundamental research - not as a standalone thesis driver. "
            "Recommend continued monitoring with monthly re-validation."
        )
    elif signal_result.reliable:
        recommendation = (
            "Signal is statistically measurable but weak. Not recommended as a standalone input; "
            "may still be useful combined with other alt-data sources."
        )
    else:
        recommendation = (
            "Insufficient sample size / unstable in-sample vs out-of-sample results to treat this "
            "as decision-grade. Recommend continuing to collect data before using in a live thesis."
        )

    filled = template.format(
        TICKER=ticker,
        START_DATE=config.START_DATE,
        END_DATE=config.END_DATE,
        completeness_summary=fmt("completeness"),
        timeliness_summary=fmt("timeliness_gaps"),
        duplicate_summary=fmt("duplicates"),
        outlier_summary=fmt("outliers"),
        n_quarters=signal_result.n_quarters,
        in_sample_corr=signal_result.in_sample_corr,
        in_sample_p=signal_result.in_sample_pvalue,
        out_of_sample_corr=signal_result.out_of_sample_corr,
        out_of_sample_p=signal_result.out_of_sample_pvalue,
        reliable=signal_result.reliable,
        caveats_list=caveats_list,
        recommendation_text=recommendation,
    )
    return filled


def main():
    print("=" * 70)
    print("STEP 1: Ingesting alt-data proxy + revenue actuals (bronze layer)")
    print("=" * 70)
    ingest.ingest_all()

    print("\n" + "=" * 70)
    print("STEP 2: Running automated data quality checks")
    print("=" * 70)
    raw = pd.read_csv(config.RAW_TRENDS_PATH, parse_dates=["date"])
    quality_results = quality_checks.run_all_checks(raw)
    quality_checks.write_quality_report(quality_results)
    print(quality_checks.summarize(quality_results))

    print("\n" + "=" * 70)
    print("STEP 3: Cleaning data + building quarterly features (silver/gold layers)")
    print("=" * 70)
    features = pipeline.run_pipeline()

    print("\n" + "=" * 70)
    print("STEP 4: Running signal validation / backtest")
    print("=" * 70)
    signal_results = signal.run_signal_evaluation(features)
    signal.write_signal_report(signal_results)
    print(signal.summarize(signal_results))

    print("\n" + "=" * 70)
    print("STEP 5: Writing PM-facing memo for each ticker")
    print("=" * 70)
    memo_sections = []
    for sig_result in signal_results:
        memo_sections.append(populate_memo(sig_result.ticker, quality_results, sig_result))
    combined_memo = "\n\n---\n\n".join(memo_sections)
    output_path = config.MEMO_DIR / "output_memo.md"
    output_path.write_text(combined_memo)
    print(f"Wrote combined memo -> {output_path}")

    print("\n" + "=" * 70)
    print("STEP 6: Example natural-language query (rule-based / offline mode)")
    print("=" * 70)
    example_ticker = list(config.TICKERS.keys())[0]
    example_question = "How did search interest trend in the most recent quarter, and how reliable is that as a signal?"
    print(f"Q ({example_ticker}): {example_question}\n")
    print(query_agent.answer_question(example_ticker, example_question))


if __name__ == "__main__":
    main()
