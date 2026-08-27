"""
Central configuration for the alt-data pipeline.

Keeping this in one place means the ingestion, quality checks, and signal
modules never hardcode tickers/thresholds independently - a single source of
truth, same as you'd want in a real production pipeline.
"""

from pathlib import Path

# --- Universe -----------------------------------------------------------
# Public retailers/consumer names with a strong, trackable digital footprint.
# Each maps to the search term(s) used as the alt-data proxy and to the
# quarterly revenue figures used as ground truth (see data/raw/revenue_actuals.csv).
TICKERS = {
    "LULU": {
        "name": "Lululemon Athletica",
        "search_terms": ["lululemon"],
    },
    "CMG": {
        "name": "Chipotle Mexican Grill",
        "search_terms": ["chipotle"],
    },
    "TGT": {
        "name": "Target",
        "search_terms": ["target"],
    },
}

# --- Date range -----------------------------------------------------------
START_DATE = "2019-01-01"
END_DATE = "2025-12-31"

# --- Paths -----------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MEMO_DIR = ROOT_DIR / "memo"

RAW_TRENDS_PATH = RAW_DIR / "search_interest_raw.csv"
RAW_REVENUE_PATH = RAW_DIR / "revenue_actuals.csv"
QUALITY_REPORT_PATH = PROCESSED_DIR / "quality_report.json"
CLEANED_PATH = PROCESSED_DIR / "search_interest_cleaned.csv"
QUARTERLY_FEATURES_PATH = PROCESSED_DIR / "quarterly_features.csv"
SIGNAL_RESULTS_PATH = PROCESSED_DIR / "signal_results.json"

# --- Data quality thresholds -----------------------------------------------------------
MAX_NULL_RATE = 0.05          # flag if >5% of expected weekly obs are missing
MAX_GAP_DAYS = 21             # flag if a gap between observations exceeds 3 weeks
OUTLIER_Z_THRESHOLD = 4.0     # flag observations beyond 4 std devs
MIN_QUARTERS_FOR_BACKTEST = 8  # don't trust a correlation with fewer data points than this
