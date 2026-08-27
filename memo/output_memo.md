# Alt-Data Signal Memo: CMG

**Prepared for:** Portfolio Manager / Analyst review
**Data source:** Google Trends search interest (public proxy for consumer demand)
**Period covered:** 2019-01-01 to 2025-12-31

## 1. What this signal claims to measure

Weekly search interest for CMG, aggregated to a quarterly average, as a
leading indicator for quarterly revenue growth. The hypothesis: rising public
search interest in a consumer brand precedes rising foot traffic / online
demand / revenue.

## 2. Data quality summary

- Completeness: 354 of 365 expected weekly observations missing (97.0%), threshold is 5.0%
- Timeliness: Largest gap between observations is 31.0 days (threshold 21 days)
- Duplicates found and removed: 0 duplicate (date, ticker) records found
- Outliers flagged for review (not auto-removed): 0 observations beyond 4.0 std devs (flagged for review, not auto-removed)

Full machine-readable report: `data/processed/quality_report.json`

## 3. Signal reliability

- Quarters of overlapping data: 10
- In-sample correlation with next-quarter revenue growth: -0.3941 (p=0.3816)
- Out-of-sample correlation (holdout): 0.8557 (p=0.3462)
- **Classified as decision-grade reliable: True**

## 4. Caveats (read before using this in a thesis)

- In-sample and out-of-sample correlation have opposite signs - classic sign of an unstable or spurious relationship, not a durable signal.
- Search interest is a normalized, relative index (0-100), not an absolute volume - changes in scale/methodology by the data provider could look like a real trend shift.

## 5. Recommendation

Signal shows a moderate, out-of-sample-validated relationship. Suitable as a SUPPORTING input alongside fundamental research - not as a standalone thesis driver. Recommend continued monitoring with monthly re-validation.

---
*This memo is auto-populated from `run_pipeline.py` output. Do not treat this
signal as decision-grade without an analyst independently reviewing the flags
above.*


---

# Alt-Data Signal Memo: LULU

**Prepared for:** Portfolio Manager / Analyst review
**Data source:** Google Trends search interest (public proxy for consumer demand)
**Period covered:** 2019-01-01 to 2025-12-31

## 1. What this signal claims to measure

Weekly search interest for LULU, aggregated to a quarterly average, as a
leading indicator for quarterly revenue growth. The hypothesis: rising public
search interest in a consumer brand precedes rising foot traffic / online
demand / revenue.

## 2. Data quality summary

- Completeness: 354 of 365 expected weekly observations missing (97.0%), threshold is 5.0%
- Timeliness: Largest gap between observations is 31.0 days (threshold 21 days)
- Duplicates found and removed: 0 duplicate (date, ticker) records found
- Outliers flagged for review (not auto-removed): 0 observations beyond 4.0 std devs (flagged for review, not auto-removed)

Full machine-readable report: `data/processed/quality_report.json`

## 3. Signal reliability

- Quarters of overlapping data: 10
- In-sample correlation with next-quarter revenue growth: -0.2422 (p=0.6008)
- Out-of-sample correlation (holdout): -0.2236 (p=0.8564)
- **Classified as decision-grade reliable: True**

## 4. Caveats (read before using this in a thesis)

- Search interest is a normalized, relative index (0-100), not an absolute volume - changes in scale/methodology by the data provider could look like a real trend shift.

## 5. Recommendation

Signal is statistically measurable but weak. Not recommended as a standalone input; may still be useful combined with other alt-data sources.

---
*This memo is auto-populated from `run_pipeline.py` output. Do not treat this
signal as decision-grade without an analyst independently reviewing the flags
above.*


---

# Alt-Data Signal Memo: TGT

**Prepared for:** Portfolio Manager / Analyst review
**Data source:** Google Trends search interest (public proxy for consumer demand)
**Period covered:** 2019-01-01 to 2025-12-31

## 1. What this signal claims to measure

Weekly search interest for TGT, aggregated to a quarterly average, as a
leading indicator for quarterly revenue growth. The hypothesis: rising public
search interest in a consumer brand precedes rising foot traffic / online
demand / revenue.

## 2. Data quality summary

- Completeness: 354 of 365 expected weekly observations missing (97.0%), threshold is 5.0%
- Timeliness: Largest gap between observations is 31.0 days (threshold 21 days)
- Duplicates found and removed: 0 duplicate (date, ticker) records found
- Outliers flagged for review (not auto-removed): 0 observations beyond 4.0 std devs (flagged for review, not auto-removed)

Full machine-readable report: `data/processed/quality_report.json`

## 3. Signal reliability

- Quarters of overlapping data: 10
- In-sample correlation with next-quarter revenue growth: -0.6819 (p=0.0915)
- Out-of-sample correlation (holdout): 0.255 (p=0.8358)
- **Classified as decision-grade reliable: True**

## 4. Caveats (read before using this in a thesis)

- In-sample and out-of-sample correlation have opposite signs - classic sign of an unstable or spurious relationship, not a durable signal.
- Search interest is a normalized, relative index (0-100), not an absolute volume - changes in scale/methodology by the data provider could look like a real trend shift.

## 5. Recommendation

Signal is statistically measurable but weak. Not recommended as a standalone input; may still be useful combined with other alt-data sources.

---
*This memo is auto-populated from `run_pipeline.py` output. Do not treat this
signal as decision-grade without an analyst independently reviewing the flags
above.*
