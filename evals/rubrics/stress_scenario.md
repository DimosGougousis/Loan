# Eval Rubric — Stress Scenario

> **Status:** Placeholder. Populated in Day 2 MID #3.

## Purpose

For each of the 4 NL stress scenarios (DNB house-price, HRA phase-out, *rentevast* reset, energy-label transition), the eval pins the portfolio-EL delta to a hand-calculated expected value and asserts it stays within ±2% across runs.

This catches silent regressions in the stress engine — exactly the kind of issue AI-generated code can introduce when a sign, a unit, or a cohort filter is wrong.

## Pass criteria

- Each scenario × parameter pair runs without exception.
- Computed EL delta is within ±2% of the value pinned in `evals/datasets/stress_expected.json`.
- No NaN or Inf in the stressed portfolio.
- The waterfall reconciles within €1 (rounding) to the total delta.

## Failure handling

- If any scenario produces a delta outside the band, eval is FAILED.
- Per `docs/governance/fail-gracefully.md` §7.7.1 stage 5: requires 2nd-line review before advancing.

## Paired test

`tests/integration/test_stress_scenario.py` (created in Day 2 MID #3).

## Source

- EBA stress-test methodology (scenario structure)
- DNB sectoral guidance (house-price shock magnitudes, rentevast cohort)
- DNB climate stress test (energy-label transition)
