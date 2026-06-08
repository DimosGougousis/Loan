# Model Inventory

> Every quantitative rule in the platform — SICR thresholds, stress uplift functions, LGD curves, anomaly detector thresholds, validation rules — appears here.

## Inventory

| Name | Module | Version | Owner | Eval | Last reviewed | Source regulation |
|---|---|---|---|---|---|---|
| _populated during Days 1–2 builds_ | | | | | | |

## Add an entry when:

- A new SICR trigger is added (`src/loan_tape/ecl/sicr.py`).
- A new stress scenario is added (`src/loan_tape/analytics/stress.py`).
- A new validation rule with calibrated thresholds (`src/loan_tape/validate/rules.py`).
- A change to the LTV→LGD curve, PD-DSCR multiplier, or any other calibrated constant.

## Entry template

```
| trigger/scenario/rule name | src/path | vX.Y | owner_name | evals/rubrics/<name>.md | YYYY-MM-DD | EBA GL/2017/06 par. X / DNB guidance Y / IFRS 9 par. Z |
```

## Quarterly review

2nd line reviews every entry every 90 days. Entries with `last_reviewed > 6 months` are auto-flagged on the governance dashboard.
