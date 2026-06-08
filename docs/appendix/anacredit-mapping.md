# Appendix A — AnaCredit Attribute Crosswalk

> Maps every AnaCredit attribute (ECB Reg 2016/867, Annex II) used by the platform to its source field in `src/loan_tape/schema.py`. Demonstrating this mapping in a real artifact is rare among credit-risk candidates and lands hard with a Dutch-bank interview panel.

## Crosswalk

| AnaCredit attribute | Dataset | Source field in `schema.py` | Derivation |
|---|---|---|---|
| Contract identifier | Instrument | `loan_id` | direct |
| Counterparty identifier | Counterparty | `borrower_id` | direct |
| Inception date | Instrument | `origination_date` | direct |
| Settlement date | Instrument | `origination_date` | direct (residential mortgages: inception = settlement) |
| Legal final maturity date | Instrument | `maturity_date` | direct |
| Reference date | All | run-time | computed at ingest |
| Currency | Instrument | `currency` | direct (always EUR for this portfolio) |
| Outstanding nominal amount | Financial | `current_balance` | direct |
| Commitment amount at inception | Instrument | `original_principal` | direct |
| Type of instrument | Instrument | constant `"Mortgage loan"` | derived |
| Type of interest rate | Instrument | `rate_type` | enum mapping: `VARIABEL` → "Variable", `RENTEVAST_*` → "Fixed" |
| Interest rate | Financial | `interest_rate` | direct |
| Interest rate reset frequency | Instrument | derived from `rate_type` + `rentevast_einddatum` | "At rentevast end" or "Continuous" |
| Repayment rights | Instrument | `repayment_type` | enum mapping |
| Project finance loan | Instrument | constant `false` | residential mortgages are not project finance |
| Type of securitisation | Instrument | constant `"Not securitised"` | (extend later if RMBS pool) |
| Performing status of the instrument | Financial | derived from `arrears_bucket` + `ifrs9_stage` | "Performing" / "Non-performing" |
| Default status of the instrument | Financial | derived from `ifrs9_stage == 3` | "Default" / "Not in default" |
| Default status of the counterparty | Counterparty | aggregated max over all loans of `borrower_id` | "Default" if any loan in default |
| Date of the default status | Financial | min `arrears_bucket >= "90+"` start date | computed |
| Type of protection | Protection | `property_type` + `nhg_flag` | "Residential real estate" + optional "NHG guarantee" |
| Protection value | Protection | `taxatie_waarde` | direct |
| Type of protection value | Protection | `taxatie_type` | enum mapping: `MARKETVALUE` → "Market value", `EXECUTIEWAARDE` → "Notional amount", `MODELMATIG` → "Other" |
| Protection valuation date | Protection | `taxatie_date` | direct |
| Real-estate location (postal code) | Protection | `pc6` | direct |
| Real-estate location (country) | Protection | constant `"NL"` | (extend if cross-border) |
| Construction year of real estate | Protection | `bouwjaar` | direct |
| Energy performance certificate | Protection | `energy_label` | enum mapping (A++++ → "A+++" capped per ECB convention) |
| Forbearance status | Financial | `restructured_flag` | "Forborne" / "Not forborne" |
| Forbearance and renegotiation status | Financial | `restructured_flag` (24mo window) | computed |
| Accounting classification (IFRS 9) | Accounting | `ifrs9_stage` | direct enum mapping |
| Accumulated impairment amount | Accounting | `expected_loss` | direct |
| Sources of encumbrance | Protection | constant `"Not encumbered"` | (extend if collateral re-pledged) |
| LTV at origination | Instrument | derived from `original_principal / property_value_at_origination` | computed |
| Current LTV | Financial | `current_ltv` | direct |
| Probability of default | Financial | `pd_12m` (point-in-time) / `pd_lifetime` (through-the-cycle) | direct |
| Loss given default | Financial | `lgd` | direct |
| Exposure at default | Financial | `ead` | direct |
| Risk weight | Financial | `risk_weight` | direct |

## Conformance check

`src/loan_tape/validate/anacredit.py::check_anacredit_conformance(loan)` returns:

```python
ConformanceResult(
    loan_id=loan.loan_id,
    populated=<bool>,         # every required attribute non-null
    enumerated=<bool>,         # every enum-typed attribute within ECB-allowed values
    missing_attributes=[...],
    invalid_values=[...],
)
```

Per `docs/governance/fail-gracefully.md` §7.7.1: if any required attribute is null, the stage advances with `WARNING` and cannot reach `Publish` without resolution.

## See also

- `docs/regulation-map.md` — AnaCredit citation
- `src/loan_tape/validate/anacredit.py` — implementation
- ECB Regulation (EU) 2016/867 — AnaCredit primary source
