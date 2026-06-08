---
name: add-sicr-trigger
description: Add an IFRS 9 SICR (Significant Increase in Credit Risk) trigger — NL-tuned. Use when EBA / DNB guidance or internal credit policy adds a Stage-2 condition.
---

# Add a SICR Trigger

## When to use

- EBA updates GL/2017/06 with a new SICR criterion.
- DNB issues sectoral / climate / macro guidance imposing an overlay.
- Internal credit policy adds a forbearance, watchlist, or behavioral trigger.

## Procedure

1. **Failing test first** in `tests/unit/ecl/test_sicr.py`:
   ```python
   def test_climate_transition_trigger_promotes_old_low_label_to_stage_2():
       loan = build_loan(
           ifrs9_stage=Stage.ONE,
           energy_label=EnergyLabel.F,
           bouwjaar=1985,
           pd_lifetime=0.03,
       )
       stage, reasons = evaluate_sicr(loan)
       assert stage == Stage.TWO
       assert SicrTrigger.CLIMATE_TRANSITION in reasons
   ```

2. **Extend the `SicrTrigger` enum** in `src/loan_tape/schema.py`.

3. **Implement the rule** in `src/loan_tape/ecl/sicr.py`:
   ```python
   def _climate_transition_trigger(loan: Loan) -> bool:
       """Soft Stage-2 trigger: legacy low-energy-label collateral.
       Source: DNB Guidance on climate risk for banks (2024), section on energy efficiency exposure.
       """
       return (
           loan.energy_label in {EnergyLabel.E, EnergyLabel.F, EnergyLabel.G}
           and loan.bouwjaar < 1992
       )
   ```

4. **Register in `SICR_TRIGGERS`** dict at the bottom of `sicr.py`.

5. **Run the test.**

6. **Add a positive + negative fixture row** to `evals/datasets/sicr_fixture.parquet` and update `evals/rubrics/sicr_triggers.md` to require 100% recall on positives and 0 false-positives on the new control.

7. **Update `docs/governance/model-inventory.md`** with: trigger name, owner, version, eval, last-reviewed date, source regulation.

8. **Update `docs/regulation-map.md`** with the source.

## Existing triggers (do not duplicate)

| Trigger | Source |
|---|---|
| `QUANT_PD_INCREASE` | EBA GL/2017/06 + NL practice: `pd_lifetime / pd_lifetime_at_origination > 2.5×` AND uplift > 0.5pp |
| `DPD_30_BACKSTOP` | IFRS 9 par. 5.5.11 |
| `FORBEARANCE` | EBA forbearance definition |
| `WATCHLIST` | Internal credit policy |
| `MACRO_OVERLAY` | DNB 2024 sectoral guidance: `rentevast_einddatum` within 12mo AND DSCR < 1.2 |
| `CLIMATE_TRANSITION` | DNB climate risk guidance |

Stage 3 backstop (separate from SICR): `days_past_due ≥ 90` OR `unlikely_to_pay_flag`.

## Eval gate

Regulated path. PR requires updated eval rubric + model-inventory + `2nd-line-approved` label.

## Checklist

- [ ] Failing test with explicit positive case
- [ ] Negative test (loan that should remain Stage 1)
- [ ] `SicrTrigger` enum extended
- [ ] Rule implementation cites EBA / DNB / IFRS source
- [ ] Registered in `SICR_TRIGGERS`
- [ ] Eval fixture has positive + negative + rubric updated
- [ ] Model inventory updated
- [ ] Regulation map updated
- [ ] `2nd-line-approved` label on PR
- [ ] `[ai-assisted]` commit
