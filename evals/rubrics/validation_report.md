# Eval Rubric — Validation Report

> Paired test: ``tests/integration/test_validation_report.py``.
>
> Owner line: 1st line (build), 2nd line (approve threshold changes).

## Purpose

The validation engine in `src/loan_tape/validate/rules.py` and the AnaCredit
mapper in `src/loan_tape/validate/anacredit.py` together produce the loan-tape
validation report (BCBS 239 + AnaCredit conformance). This rubric pins their
behavior under regression.

## Pass criteria

| # | Criterion | Test |
|---|---|---|
| 1 | **≥ 95% recall** on each seeded easter-egg cohort that maps to a rule | `test_eval_easter_egg_recall_meets_95pct` |
| 2 | **0 false-positive CRITICAL** findings on the clean ``golden_tape.parquet`` | `test_eval_no_false_positive_criticals_on_clean_tape` |
| 3 | **AnaCredit conformance ≥ 98%** on the clean tape | `test_eval_anacredit_conformance_on_clean_tape` |
| 4 | Every CRITICAL finding carries a regulation citation | `test_eval_every_critical_cites_a_regulation` |

## Easter eggs (cohorts and their target rules)

| Easter egg | Target rule | Notes |
|---|---|---|
| `NHG_CAP_BREACH_BATCH` | `nhg_cap` (CRITICAL) | Every row should surface |
| `HIGH_INTEREST_ONLY_CLUSTER` | `interest_only_cap` (HIGH) | HRA-eligible only |
| `STALE_TAXATIE_CLUSTER` | `taxatie_freshness` (MEDIUM) | Only Stage 1 loans tested |
| `HIGH_AFLOSSINGSVRIJ_COHORT` | (anomaly detector — Day 2 PM #1) | Not validated by rules |

## Failure handling

- If any rubric criterion fails → eval FAILED → blocks merge (regulated path
  per `docs/governance/change-management.md`).
- Eval flake (≥ 4/5 reruns pass) → marked FLAKY, requires 2nd-line override
  with reasoning logged in `docs/governance/decisions.md`.

## Source citations

- IFRS 9 par. 5.5.11 (Stage 3 backstop)
- EBA GL/2017/06 (SICR thresholds — exercised indirectly via `stage_3_backstop`)
- NHG / WEW (annual cap publication)
- *Tijdelijke regeling hypothecair krediet* (LTI cap)
- *Hypotheekrenteaftrek* regime, post-2013 (Belastingdienst)
- BCBS 239 (data-quality dimensions: accuracy / completeness / timeliness / integrity)
- ECB Reg 2016/867 Annex II (AnaCredit)
