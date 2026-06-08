# Reference Data

> Public reference tables used by the synthetic generator, validation rules, and stress engine. All values traceable to a public source. Updated annually.

## Files

| File | Purpose | Source | Updated |
|---|---|---|---|
| `nhg_caps.csv` | NHG cost limits per year of origination, plus energy-neutral cap from 2018, plus annual premium %. | Stichting Waarborgfonds Eigen Woningen (WEW) — annual cap publication. <https://www.nhg.nl/> | Annually (Q4). |
| `hra_rates.csv` | Maximum *hypotheekrenteaftrek* rate per tax year. Used to age the phase-out across the synthetic vintage range. | Belastingdienst / Belastingplan. | Annually. |
| `nibud_lti.csv` | Loan-to-Income factors per gross household income band per year. Used by the *Tijdelijke regeling hypothecair krediet* affordability validation rule. | Nibud + Min. Fin. + AFM annual publication. <https://www.nibud.nl/> | Annually (October for following year). |
| `pc6_to_gemeente.parquet` | Postcode → municipality lookup (synthetic subset). | Based on public CBS data — only a sample subset distributed; full table regenerated locally. | When CBS publishes updates. |

## Caveats

- **The values here are public reference values** — not modeled, not assumed. Every quantitative rule in `src/loan_tape/validate/rules.py` and `src/loan_tape/analytics/stress.py` reads from these CSVs rather than embedding magic constants.
- **Nibud LTI table is highly granular** in the real publication (1-EUR income steps, age bands, partner-income inclusion). The CSV here is a *representative snapshot* sufficient for the synthetic tape. Production use requires the full table.
- **2026 row in hra_rates.csv** is projected per the most recent Belastingplan but subject to confirmation.
- All amounts in EUR. All percentages as decimals × 100 (the column suffix `_pct` denotes percent units).

## Update procedure

When updating any of these files:

1. Pull the latest published value from the source.
2. Commit with `[ai-assisted]` (if AI helped) and link the source.
3. Append a row — never overwrite history. Past vintages must reference the value that was current at their origination year.
4. Update `docs/governance/model-inventory.md` if a value drives a quantitative rule.
5. Run the validation eval suite on the easter-egg fixture to confirm no regression: `uv run python evals/runner.py --rubric validation_report`.
