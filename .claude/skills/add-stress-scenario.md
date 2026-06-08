---
name: add-stress-scenario
description: Add a new NL-tuned stress scenario to the stress engine. Use for DNB / EBA / climate / regulatory scenarios.
---

# Add a Stress Scenario

## When to use

- DNB publishes a new sectoral scenario (e.g., updated house-price stress).
- EBA biennial stress test methodology changes.
- A new internal scenario (e.g., rentevast reset, climate transition, HRA phase-out acceleration).

## Procedure

1. **Write the failing test FIRST.** `tests/unit/analytics/test_stress.py`:
   ```python
   def test_dnb_house_price_shock_minus_30pct():
       tape = load_golden_tape()
       baseline_el = portfolio_el(tape)
       stressed = apply_dnb_house_price_shock(tape, shock=-0.30)
       stressed_el = portfolio_el(stressed)
       # Hand-calculated expected delta on golden tape:
       assert (stressed_el - baseline_el) == pytest.approx(EXPECTED_DELTA_30PCT, rel=0.02)
   ```

2. **Implement as pure function** `(tape, params) -> stressed_tape` in `src/loan_tape/analytics/stress.py`.

3. **Calibrate the uplift function.**
   - House-price shock: `property_value_current *= (1 + shock)` then recompute `current_ltv` then piecewise LTV→LGD curve.
   - Rate shock: `+Δbps` to variable + resetting loans → DSCR drop → PD multiplier (calibrated).
   - HRA phase-out: accelerate `hra_phase_out_rate` → DSCR drop → PD multiplier.
   - Energy-label transition: discount `property_value_current` by 5/10/15% for D/E/F-G labels → LGD impact.

4. **Run the test.** Verify EL delta.

5. **Add the scenario to the eval rubric** `evals/rubrics/stress_scenario.md` with expected EL delta within ±2% of hand-calculated value.

6. **Wire into the UI** `app/pages/3_Stress_Testing.py`: add to scenario picker.

7. **Update `docs/governance/model-inventory.md`** with the scenario name, owner, version, eval, source regulation.

8. **Update `docs/regulation-map.md`** with the source (DNB sectoral guidance / EBA methodology / internal credit policy).

## Calibration rules

- Every multiplier or curve constant has a *source*. No magic numbers without a citation.
- LTV→LGD piecewise curve lives in `src/loan_tape/ecl/ifrs9.py::lgd_from_ltv()` — do not duplicate.
- PD uplift from DSCR drop: use the calibrated multiplier in `src/loan_tape/analytics/stress.py::PD_DSCR_MULTIPLIER` — document the source.

## Eval gate

This is a *regulated path*. The PR requires:

1. Updated eval rubric ✓
2. Updated model-inventory ✓
3. `2nd-line-approved` label on PR ✓

The governance dashboard (Tab 2) will refuse to mark the feature complete until all three are present.

## Checklist

- [ ] Failing test with hand-calculated expected EL delta
- [ ] Scenario is pure function `(tape, params) -> stressed_tape`
- [ ] Uplift constants have regulatory citation
- [ ] Eval rubric updated with ±2% tolerance
- [ ] UI scenario picker updated
- [ ] Model inventory entry added
- [ ] Regulation map updated
- [ ] PR carries `2nd-line-approved` label
- [ ] `[ai-assisted]` commit
