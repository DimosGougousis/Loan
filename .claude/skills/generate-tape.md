---
name: generate-tape
description: Extend or modify the synthetic Dutch mortgage tape generator. Use when adding fields, vintages, or easter eggs.
---

# Generate / Extend the Synthetic Tape

## When to use

- Adding a new field to `schema.py` that the generator must populate.
- Tuning a correlation (e.g., postcode → property value).
- Seeding a new easter egg for anomaly detection or validation testing.
- Backfilling a new vintage range.

## Procedure

1. **Schema first.** Add the field to `src/loan_tape/schema.py` with its enum/range constraint. Run `pytest tests/unit/test_schema.py` to confirm new constraints fire correctly on edge cases.

2. **Reference data if needed.** If the new field depends on a regulated table (NHG cap, HRA rate, Nibud LTI), add the lookup file under `data/reference/` and document its source in `data/reference/README.md`.

3. **Generator change in `src/loan_tape/generator.py`.**
   - Pure function: `generate_tape(n: int, seed: int) -> pl.DataFrame`.
   - All randomness routed through one `numpy.random.Generator` initialized from `seed`.
   - Correlations: implement as conditional draws based on existing fields, not independent.

4. **TDD on the generator.**
   - Hypothesis property test: every generated tape satisfies the schema.
   - Distribution test: empirical share of the new field within tolerance of expected.
   - Determinism test: same seed → byte-identical Parquet (hash check).

5. **Easter eggs.**
   - Inject anomalies in `generator.py::_inject_easter_eggs()`.
   - Each easter egg is a named function: `_inject_aflossingsvrij_cohort()`, `_inject_stale_taxatie_cluster()`, etc.
   - Document each in `docs/domain-primer.md`.

6. **Regenerate fixtures.**
   - `uv run python -m loan_tape.generator --seed 42 --n 10000 --out data/samples/synthetic_tape_v1.parquet`
   - `uv run python -m loan_tape.generator --seed 1 --n 500 --out tests/fixtures/golden_tape.parquet`
   - Update the sha256 in `tests/unit/test_generator.py::test_golden_tape_hash`.

## NL realism rules

| Concern | Rule |
|---|---|
| Vintage mix | Pre-2013: skew AFLOSSINGSVRIJ/SPAAR. Post-2013: dominantly ANNUITEIT. |
| Geography | Randstad PC6 → higher property value (×1.2-1.8), larger loans. |
| Energy label | By bouwjaar: pre-1992 dominantly C-G; 1992-2015 mixed; post-2015 A/A+. |
| Rentevast cohort | ~25% have rentevast_einddatum in 2025-2028 (the reset wave). |
| NHG eligibility | nhg_flag → original_principal ≤ nhg_cap_at_origination (year-of-origination cap). |
| HRA eligibility | tax_deduction_eligible only when repayment_type IN {ANNUITEIT, LINEAIR} AND origination_date ≥ 2013-01-01. |

## Checklist

- [ ] Schema updated with constraints
- [ ] Reference data added if needed, with source documented
- [ ] Generator change is a pure function from (n, seed)
- [ ] Hypothesis test asserts every loan passes schema
- [ ] Determinism test pins output hash
- [ ] Easter eggs documented in `docs/domain-primer.md`
- [ ] Regenerated `synthetic_tape_v1.parquet` and `golden_tape.parquet`
- [ ] Updated hash in `test_generator.py`
- [ ] `[ai-assisted]` commit
