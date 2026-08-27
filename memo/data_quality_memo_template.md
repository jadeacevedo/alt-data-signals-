# Alt-Data Signal Memo: {TICKER}

**Prepared for:** Portfolio Manager / Analyst review
**Data source:** Google Trends search interest (public proxy for consumer demand)
**Period covered:** {START_DATE} to {END_DATE}

## 1. What this signal claims to measure

Weekly search interest for {TICKER}, aggregated to a quarterly average, as a
leading indicator for quarterly revenue growth. The hypothesis: rising public
search interest in a consumer brand precedes rising foot traffic / online
demand / revenue.

## 2. Data quality summary

- Completeness: {completeness_summary}
- Timeliness: {timeliness_summary}
- Duplicates found and removed: {duplicate_summary}
- Outliers flagged for review (not auto-removed): {outlier_summary}

Full machine-readable report: `data/processed/quality_report.json`

## 3. Signal reliability

- Quarters of overlapping data: {n_quarters}
- In-sample correlation with next-quarter revenue growth: {in_sample_corr} (p={in_sample_p})
- Out-of-sample correlation (holdout): {out_of_sample_corr} (p={out_of_sample_p})
- **Classified as decision-grade reliable: {reliable}**

## 4. Caveats (read before using this in a thesis)

{caveats_list}

## 5. Recommendation

{recommendation_text}

---
*This memo is auto-populated from `run_pipeline.py` output. Do not treat this
signal as decision-grade without an analyst independently reviewing the flags
above.*
