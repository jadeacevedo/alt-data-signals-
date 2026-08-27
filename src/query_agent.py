"""
Natural-language query layer over the pipeline's output ("AI readiness" piece
of the role).

The key design principle: the LLM is NOT the source of truth. It's a
presentation layer on top of the cleaned, documented dataset and signal
results. The context object built in `build_context()` is what actually
grounds the answer - the model is instructed to only reason over that context
and to always surface the caveats attached to the data, rather than treating
retrieval as decorative.

Works in two modes:
  - Offline / rule-based (default): no API key needed, always works, good for
    demos and for showing you understand the underlying logic without relying
    on a model.
  - LLM-grounded (if ANTHROPIC_API_KEY is set): sends the same structured
    context to Claude and asks it to answer in natural language, still
    required to cite the caveats.
"""

from __future__ import annotations

import argparse
import json
import os

import pandas as pd

import config


def build_context(ticker: str) -> dict:
    """Assemble everything the query layer is allowed to reason over for a given ticker."""
    features = pd.read_csv(config.QUARTERLY_FEATURES_PATH)
    ticker_features = features[features["ticker"] == ticker].sort_values("quarter")

    with open(config.SIGNAL_RESULTS_PATH) as f:
        signal_results = json.load(f)
    ticker_signal = next((r for r in signal_results if r["ticker"] == ticker), None)

    with open(config.QUALITY_REPORT_PATH) as f:
        quality_results = json.load(f)
    ticker_quality = [r for r in quality_results if r["ticker"] in (ticker, "ALL")]

    recent = ticker_features.tail(4).to_dict(orient="records")

    return {
        "ticker": ticker,
        "recent_quarters": recent,
        "signal_summary": ticker_signal,
        "data_quality_flags": [q for q in ticker_quality if not q["passed"]],
    }


def _rule_based_answer(context: dict) -> str:
    """Offline fallback: deterministic natural-language summary of the context object."""
    ticker = context["ticker"]
    recent = context["recent_quarters"]
    signal = context["signal_summary"]

    if len(recent) < 2:
        return f"Not enough recent quarterly data for {ticker} to compare trends."

    latest, prior = recent[-1], recent[-2]
    delta = latest["avg_search_interest"] - prior["avg_search_interest"]
    direction = "up" if delta > 0 else "down"

    lines = [
        f"{ticker}: average search interest in {latest['quarter']} was "
        f"{latest['avg_search_interest']:.1f}, {direction} {abs(delta):.1f} points versus "
        f"{prior['quarter']} ({prior['avg_search_interest']:.1f}).",
    ]

    if signal:
        lines.append(
            f"Historical reliability: out-of-sample correlation with next-quarter revenue "
            f"growth is {signal['out_of_sample_corr']} across {signal['n_quarters']} quarters "
            f"(reliable={signal['reliable']})."
        )
        for c in signal["caveats"]:
            lines.append(f"Caveat: {c}")

    if context["data_quality_flags"]:
        lines.append("Open data quality flags:")
        for flag in context["data_quality_flags"]:
            lines.append(f"  - {flag['check_name']}: {flag['detail']}")

    return "\n".join(lines)


def _llm_answer(context: dict, question: str) -> str:
    """LLM-grounded answer. Requires ANTHROPIC_API_KEY to be set."""
    import anthropic

    client = anthropic.Anthropic()
    system_prompt = (
        "You are a data assistant for equity research analysts at a long/short "
        "equity fund. You must answer ONLY using the JSON context provided - do "
        "not use outside knowledge about the company. Always explicitly mention "
        "any caveats or data quality flags present in the context, even if the "
        "user didn't ask about them. If the signal is not marked reliable, say "
        "so plainly and do not overstate confidence."
    )
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Context:\n{json.dumps(context, indent=2)}\n\nQuestion: {question}",
        }],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def answer_question(ticker: str, question: str) -> str:
    context = build_context(ticker)
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _llm_answer(context, question)
        except Exception as exc:  # noqa: BLE001
            return f"[LLM call failed ({exc}), falling back to rule-based answer]\n\n" + _rule_based_answer(context)
    return _rule_based_answer(context)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the alt-data pipeline in natural language.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. LULU")
    parser.add_argument("--question", required=True, help="Natural language question")
    args = parser.parse_args()

    print(answer_question(args.ticker, args.question))
