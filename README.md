# Alt Data Signal Pipeline for Retail Earnings Prediction

A end-to-end alternative data pipeline that mirrors the workflow of a fundamental
long/short equity fund: ingest a noisy public alt-data proxy (Google Trends search
interest), clean and validate it, test whether it actually predicts a public
retailer's quarterly revenue, and expose the results through a natural-language
query layer an analyst could use.

This project is built to demonstrate the exact skillset needed for an
**Alternative Data / AI Data Engineer** role at a long/short equity fund:

- Building reliable, observable data pipelines (bronze -> silver -> gold layers)
- Automated data quality checks (completeness, timeliness, outliers, schema drift)
- Signal validation with proper backtesting discipline (no look-ahead bias,
  out-of-sample testing, honest treatment of small-sample risk)
- Grounding an LLM/RAG-style query layer in clean, documented data rather than
  treating "AI" as a black box

## Why Google Trends as the alt-data proxy?

Real alternative data (credit card panels, point-of-sale data) is proprietary and
expensive. Google Trends search-interest data is free, public, and shares the same
core properties that make alt data useful *and* risky for a fund:

- It's a **noisy, indirect proxy** for real business activity (search interest in
  a brand is not the same as revenue)
- It's **normalized and relative**, not an absolute count (0-100 scale) - a
  classic "know your data's limitations" problem
- It can have **regime changes / methodology shifts** and gaps, just like real
  vendor data

The pipeline is written so that swapping in a real vendor feed (credit card panel,
POS data, web traffic) only requires changing `src/ingest.py` - everything
downstream (quality checks, signal testing, query layer) stays the same.

## Project layout

```
alt-data-signal-pipeline/
├── README.md
├── requirements.txt
├── config.py                  # tickers, date ranges, thresholds
├── data/
│   ├── raw/                   # bronze layer - raw pulls, untouched
│   └── processed/             # silver/gold layers - cleaned, analysis-ready
├── src/
│   ├── ingest.py               # pulls alt-data proxy + revenue data (bronze layer)
│   ├── quality_checks.py       # automated data quality checks
│   ├── pipeline.py             # orchestrates bronze -> silver -> gold
│   ├── signal.py                # correlation / lead-lag / backtest analysis
│   └── query_agent.py          # natural-language query layer over the dataset
├── memo/
│   └── data_quality_memo_template.md   # PM-facing writeup template
├── tests/
│   └── test_quality_checks.py
└── run_pipeline.py             # single entrypoint: run everything end to end
```

## Quickstart

```bash
pip install -r requirements.txt
python run_pipeline.py
```

This will:
1. Ingest data (real Google Trends pull if `pytrends` succeeds and network is
   available; otherwise falls back to a documented synthetic generator so the
   pipeline is always runnable and testable)
2. Run automated data quality checks and write a quality report
3. Clean and align the alt-data series with quarterly revenue
4. Run correlation / lead-lag analysis and an out-of-sample backtest
5. Print a summary you could hand to a PM, and save `memo/output_memo.md`

Then try the query layer:

```bash
python -m src.query_agent --ticker LULU --question "How did search interest trend in the most recent quarter versus the one before, and how reliable is that as a signal?"
```

(Query layer works fully offline with a rule-based fallback; if you set
`ANTHROPIC_API_KEY`, it upgrades to an LLM-generated answer grounded in the same
underlying data + documented caveats.)

## Design decisions worth mentioning in an interview

- **Bronze/silver/gold layering**: raw pulls are never mutated in place, so a bad
  cleaning step can always be re-run from source.
- **No look-ahead bias**: the backtest only ever uses alt-data observations dated
  before a given quarter's earnings date when predicting that quarter.
- **Every signal claim ships with its caveats**: sample size, R², and known
  limitations are attached to the output object itself, not just mentioned in
  prose, so the query layer can't "forget" to disclose them.
- **Schema drift handling**: `ingest.py` validates incoming data against an
  expected schema and quarantines rows that don't match instead of silently
  dropping or crashing.
