# Alt Data Signal Pipeline for Retail Earnings Prediction

A end-to-end alternative data pipeline that mirrors the workflow of a fundamental
long/short equity fund: ingest a noisy public alt-data proxy (Google Trends search
interest), clean and validate it, test whether it actually predicts a public
retailer's quarterly revenue, and expose the results through a natural-language
query layer an analyst could use.
this project demonstrates: 
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
## design decision 

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

## output 
@jadeacevedo ➜ /workspaces/alt-data-signals- (main) $  python run_pipeline.py
======================================================================
STEP 1: Ingesting alt-data proxy + revenue actuals (bronze layer)
======================================================================
2026-08-27 18:12:47,817 [INFO] Ingesting LULU (Lululemon Athletica)...
2026-08-27 18:12:48,158 [INFO] Ingesting CMG (Chipotle Mexican Grill)...
2026-08-27 18:12:48,412 [INFO] Ingesting TGT (Target)...
2026-08-27 18:12:48,724 [INFO] Wrote raw search interest -> /workspaces/alt-data-signals-/data/raw/search_interest_raw.csv (252 rows)
2026-08-27 18:12:48,724 [INFO] Wrote raw revenue actuals -> /workspaces/alt-data-signals-/data/raw/revenue_actuals.csv (84 rows)

======================================================================
STEP 2: Running automated data quality checks
======================================================================
Data quality checks: 7/13 passed.
  [FAILED] completeness (LULU): 354 of 365 expected weekly observations missing (97.0%), threshold is 5.0%
  [FAILED] timeliness_gaps (LULU): Largest gap between observations is 31.0 days (threshold 21 days)
  [FAILED] completeness (CMG): 354 of 365 expected weekly observations missing (97.0%), threshold is 5.0%
  [FAILED] timeliness_gaps (CMG): Largest gap between observations is 31.0 days (threshold 21 days)
  [FAILED] completeness (TGT): 354 of 365 expected weekly observations missing (97.0%), threshold is 5.0%
  [FAILED] timeliness_gaps (TGT): Largest gap between observations is 31.0 days (threshold 21 days)

======================================================================
STEP 3: Cleaning data + building quarterly features (silver/gold layers)
======================================================================
2026-08-27 18:12:48,779 [INFO] Wrote cleaned search interest -> /workspaces/alt-data-signals-/data/processed/search_interest_cleaned.csv (132 rows)
2026-08-27 18:12:48,786 [INFO] Wrote quarterly features -> /workspaces/alt-data-signals-/data/processed/quarterly_features.csv (33 rows)

======================================================================
STEP 4: Running signal validation / backtest
======================================================================

CMG: n=10 quarters
  In-sample corr:      -0.2533 (p=0.5836)
  Out-of-sample corr:  0.9998 (p=0.0134)
  Reliable enough for decision-grade use: True
  - Caveat: In-sample and out-of-sample correlation have opposite signs - classic sign of an unstable or spurious relationship, not a durable signal.
  - Caveat: Search interest is a normalized, relative index (0-100), not an absolute volume - changes in scale/methodology by the data provider could look like a real trend shift.

LULU: n=10 quarters
  In-sample corr:      -0.1977 (p=0.6709)
  Out-of-sample corr:  -0.2309 (p=0.8516)
  Reliable enough for decision-grade use: True
  - Caveat: Search interest is a normalized, relative index (0-100), not an absolute volume - changes in scale/methodology by the data provider could look like a real trend shift.

TGT: n=10 quarters
  In-sample corr:      -0.6868 (p=0.0883)
  Out-of-sample corr:  0.371 (p=0.7581)
  Reliable enough for decision-grade use: True
  - Caveat: In-sample and out-of-sample correlation have opposite signs - classic sign of an unstable or spurious relationship, not a durable signal.
  - Caveat: Search interest is a normalized, relative index (0-100), not an absolute volume - changes in scale/methodology by the data provider could look like a real trend shift.

======================================================================
STEP 5: Writing PM-facing memo for each ticker
======================================================================
Wrote combined memo -> /workspaces/alt-data-signals-/memo/output_memo.md

======================================================================
STEP 6: Example natural-language query (rule-based / offline mode)
======================================================================
Q (LULU): How did search interest trend in the most recent quarter, and how reliable is that as a signal?

LULU: average search interest in 2025Q2 was 70.0, down 28.3 points versus 2024Q4 (98.3).
Historical reliability: out-of-sample correlation with next-quarter revenue growth is -0.2309 across 10 quarters (reliable=True).
Caveat: Search interest is a normalized, relative index (0-100), not an absolute volume - changes in scale/methodology by the data provider could look like a real trend shift.
Open data quality flags:
  - completeness: 354 of 365 expected weekly observations missing (97.0%), threshold is 5.0%
  - timeliness_gaps: Largest gap between observations is 31.0 days (threshold 21 days)

# summary 
The alternative-data pipeline successfully ingested, cleaned, and evaluated search-interest data for Lululemon (LULU), Chipotle Mexican Grill (CMG), and Target (TGT) against quarterly revenue actuals. However, the current dataset presents significant data-quality limitations that reduce confidence in the resulting signals. Each ticker experienced approximately 97% missing weekly observations, with the largest observation gap reaching 31 days versus a 21-day threshold. While the pipeline was able to construct quarterly features, the limited underlying observations warrant caution when interpreting the results. LULU showed a weak and statistically insignificant out-of-sample relationship between search interest and subsequent revenue growth (correlation: -0.23; p=0.85), providing no meaningful evidence of predictive value. TGT showed a stronger negative in-sample relationship but this reversed out-of-sample (from -0.69 to +0.37), indicating an unstable relationship with no statistically significant predictive power. CMG produced an unusually strong out-of-sample correlation of 0.9998 (p=0.013), but this result should not be treated as decision-grade because the relationship reversed direction between the in-sample and out-of-sample periods, raising the possibility of a spurious or sample-specific effect. Overall, the analysis suggests that search interest may provide useful descriptive context around consumer demand, but the current evidence does not support using the signals as standalone revenue predictors. Additional historical observations, improved weekly data coverage, and more robust out-of-sample validation are recommended before incorporating these alternative-data signals into investment decisions.
