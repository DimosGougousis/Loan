---
name: "source-command-stress-run"
description: "Run a named stress scenario on the default tape and print EL delta + waterfall summary."
---

# source-command-stress-run

Use this skill when the user asks to run the migrated source command `stress-run`.

## Command Template

# /stress-run <scenario>

Execute a single stress scenario for quick iteration.

## Procedure

1. Load the default tape (`data/samples/synthetic_tape_v1.parquet`) unless `--tape` is provided.
2. Resolve `<scenario>` to a scenario function in `src/loan_tape/analytics/stress.py`. Valid: `dnb_house_price`, `hra_phase_out`, `rentevast_reset`, `energy_label_transition`.
3. Run baseline ECL → run stressed ECL → compute delta.
4. Print a compact summary:
   ```
   Scenario:           dnb_house_price (shock=-0.30)
   Baseline EL:        EUR 12,450,000
   Stressed EL:        EUR 18,720,000
   Delta:              +EUR 6,270,000 (+50.4%)
   Waterfall:          [...top contributing cohorts...]
   Verification:       Within ±2% of expected (eval rubric: stress_scenario)
   ```
5. Append a row to `pipeline_runs` in `governance_state.duckdb` with `stage='STRESS_RUN'`.

## Iron Law

Read the printed delta. Sanity-check sign and magnitude. A negative delta on a downside shock is a code bug, not a "model surprise".

## Reference

- `.Codex/skills/add-stress-scenario.md`
- `src/loan_tape/analytics/stress.py`
