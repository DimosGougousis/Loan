# Eval Rubric — Validation Report

> **Status:** Placeholder. Populated in Day 1 PM #3.

## Purpose

The validation engine in `src/loan_tape/validate/rules.py` must catch ≥ 95% of the issues seeded into `evals/datasets/validation_easter_eggs.parquet`. This includes all 9 NL-specific cross-field rules from §5.5 of the plan.

## Pass criteria

- ≥ 95% of seeded issues surface with the correct severity.
- 0 false-positive CRITICAL findings on a clean tape (`tests/fixtures/golden_tape.parquet`).
- Every CRITICAL finding includes a regulation citation.
- AnaCredit conformance ≥ 98% on the clean tape.

## Categories of seeded issues

1. NHG cap breach (`nhg_flag=True` AND `original_principal > nhg_cap_at_origination`).
2. HRA non-conformance (`tax_deduction_eligible=True` AND `repayment_type IN {AFLOSSINGSVRIJ, BANKSPAAR, ...}`).
3. LTV computation drift (`current_ltv` ≠ `current_balance / property_value_current`).
4. Stale taxatie (Stage 1 loan with `taxatie_date` > 36 months old).
5. Stage 3 without dpd≥90 and without UTP flag.
6. PD monotonicity (`pd_lifetime < pd_12m`).
7. Negative amortization (`current_balance > original_principal × 1.001`).
8. LTI cap breach (`original_lti > nibud_lti_cap(origination_year, gross_income)`).
9. Interest-only ratio > 50% on HRA-eligible loan.

## Failure handling

- If recall < 95% → eval FAILED → blocks merge.
- If any false-positive CRITICAL on the clean tape → eval FAILED.

## Paired test

`tests/integration/test_validation_report.py` (created in Day 1 PM #3).

## Source

- IFRS 9 (stage 3 backstop)
- NHG / WEW (annual cap)
- *Tijdelijke regeling hypothecair krediet* (LTI cap)
- Nibud norms (LTI table)
- BCBS 239 (data quality dimensions)
