# Eval Rubric — SICR Triggers

> **Status:** Placeholder. Populated in Day 2 AM #3.

## Purpose

NL-tuned IFRS 9 SICR triggers in `src/loan_tape/ecl/sicr.py` must correctly promote every loan that meets a trigger condition to Stage 2 (or 3 for the dpd backstop), and must NOT promote control loans that look superficially similar but do not meet the condition.

## Pass criteria

- **Recall:** 100% of seeded positive loans in `evals/datasets/sicr_fixture.parquet` land in Stage ≥ 2.
- **Specificity:** 0% of control loans are promoted to Stage 2.
- Each of the 6 triggers (QUANT_PD_INCREASE, DPD_30_BACKSTOP, FORBEARANCE, WATCHLIST, MACRO_OVERLAY, CLIMATE_TRANSITION) has at least 2 positive fixtures and at least 1 negative control.

## Failure handling

- If recall < 100%, eval is FAILED → blocks merge (regulated path).
- If false-positive rate > 0%, eval is FAILED.

## Paired test

`tests/integration/test_sicr_triggers.py` (created in Day 2 AM #3).

## Source

- IFRS 9 par. 5.5.11 (30 dpd backstop)
- EBA GL/2017/06 (SICR guidelines)
- EBA forbearance definition
- DNB 2024 sectoral guidance (rentevast macro overlay)
- DNB climate risk guidance (climate transition soft trigger)
