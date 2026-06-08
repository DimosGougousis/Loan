---
name: add-anomaly-detector
description: Add a feature or rule to the anomaly / drift detection module. Use for new behavioral signals or drift dimensions.
---

# Add an Anomaly Detector

## When to use

- A new feature should enter the isolation-forest input set.
- A new drift dimension should be KS-tested between recent and baseline vintages.
- A new rule-based anomaly (e.g., "loan with `interest_only_portion > 0.5 × property_value`") should be surfaced.

## Procedure

1. **Failing test first** in `tests/unit/analytics/test_anomaly.py`:
   ```python
   def test_isolation_forest_surfaces_seeded_interest_only_cohort():
       tape = load_easter_egg_tape()  # contains the seeded cohort
       anomalies = detect_anomalies(tape, top_n=20)
       offending_ids = set(tape.filter(pl.col("interest_only_portion") > 0.5 * pl.col("property_value_at_origination"))["loan_id"])
       surfaced_ids = {a.loan_id for a in anomalies}
       assert offending_ids.issubset(surfaced_ids)
   ```

2. **Implement in `src/loan_tape/analytics/anomaly.py`.**
   - Isolation-forest feature set: extend `ANOMALY_FEATURES` tuple.
   - Rule-based: add to `RULE_BASED_ANOMALIES` list.
   - Drift dimension: add to `DRIFT_DIMENSIONS` tuple — each entry is `(feature, baseline_window_quarters)`.

3. **Per-loan reason strings.** Each anomaly returns:
   ```python
   Anomaly(
       loan_id=...,
       score=...,
       reason="interest_only_portion (0.62) exceeds 0.5 × property_value_at_origination (0.50) — HRA non-conformance risk",
       triggered_features=["interest_only_portion", "property_value_at_origination"],
   )
   ```
   Reason strings are user-facing. They cite the cohort, the deviation, and the implication.

4. **Drift detector contract.**
   - Compare most recent vintage vs trailing 4-quarter baseline by default.
   - KS-test per feature with Bonferroni correction across features.
   - Output: `DriftResult(feature, ks_stat, p_value, baseline_mean, recent_mean, verdict)`.

5. **Fail gracefully** per §7.7.1: if isolation forest fails to converge, fall back to rule-based list and log `degraded_mode=True` on the run.

6. **Run the test.**

## Feature selection rules

| Concern | Rule |
|---|---|
| Numeric features | Z-score scale before isolation forest input |
| Categorical features | One-hot encode only if cardinality < 10 |
| Sparse features | Exclude features with > 80% null |
| Date features | Convert to "months since origination" first |

## Checklist

- [ ] Failing test using easter-egg tape from `data/samples/`
- [ ] Implementation extends `ANOMALY_FEATURES` / `RULE_BASED_ANOMALIES` / `DRIFT_DIMENSIONS`
- [ ] Reason strings cite deviation + implication
- [ ] Degraded-mode fallback documented and tested
- [ ] `[ai-assisted]` commit
