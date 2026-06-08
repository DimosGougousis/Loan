# Dutch Residential Mortgage — Domain Primer

> Read this before touching `src/loan_tape/schema.py` or `src/loan_tape/generator.py`. Every field below has a reason rooted in NL retail-banking practice. A Dutch credit-risk practitioner should recognize their own portfolio in this schema.

## Why this matters

Dutch residential mortgages are the largest asset class on ING / Rabobank / ABN AMRO / de Volksbank balance sheets. They have idiosyncratic features no generic loan schema captures:

- **NHG** (Nationale Hypotheek Garantie) — a national guarantee, near-zero LGD up to a year-of-origination cap.
- **Tax-driven product mix** — *hypotheekrenteaftrek* (HRA) is only available on annuity/linear loans originated since 2013.
- **Post-2018 LTV cap** — regulatory hard cap of 100% LTV at origination.
- ***Tijdelijke regeling hypothecair krediet*** — annual LTI/LTV caps published by Min. Fin. + AFM.
- **Rate-fix cohorts** — *rentevastperiode* of 5/10/20/30 years; the 2025–2028 reset wave is a current macroprudential concern.
- **Energy label** — material to current LGD via DNB climate guidance and now to pricing.

## Schema — field-by-field

### Borrower & contract

| Field | Type | Why it matters (NL specifics) |
|---|---|---|
| `loan_id` | str (UUID) | Primary key. |
| `borrower_id` | str | Many loans → one borrower. NL: joint mortgages with `partner_income_included` common. |
| `borrower_type` | enum | `STARTER`, `DOORSTROMER`, `OUDERE` — NHG and Nibud rules differ per cohort. |
| `origination_date` | date | Pre-2013 vs. post-2013 split is **fiscally critical** (HRA eligibility). |
| `maturity_date` | date | Drives *rentevastperiode* reset clustering. |
| `original_principal` | float (EUR) | Starting EAD. |
| `current_balance` | float (EUR) | Current EAD. |
| `interest_rate` | float | Nominal annual. |
| `rate_type` | enum | `VARIABEL`, `RENTEVAST_5J`, `RENTEVAST_10J`, `RENTEVAST_20J`, `RENTEVAST_30J`. |
| `rentevast_einddatum` | date \| null | When fix expires → reset risk (material 2025–2028 cohort). |
| `repayment_type` | enum | NL-specific: `ANNUITEIT`, `LINEAIR`, `AFLOSSINGSVRIJ`, `BANKSPAAR`, `SPAAR`, `BELEGGING`, `HYBRIDE`. |
| `tax_deduction_eligible` | bool | Only `ANNUITEIT`/`LINEAIR` originated post-2013 qualify for *hypotheekrenteaftrek*. |
| `hra_phase_out_rate` | float | Max 36.97% (2025), declining from legacy 49.5%. |
| `interest_only_portion` | float | Capped at 50% of property value for HRA. |
| `currency` | str | EUR. FX risk = nil. |

### Collateral & property

| Field | Type | Why it matters |
|---|---|---|
| `property_value_at_origination` | float | Denominator of original LTV. |
| `taxatie_waarde` | float | Independent valuation (NWWI / iValidatie registered). |
| `taxatie_date` | date | Freshness — drives validation rule (≤ 36mo for Stage 1). |
| `taxatie_type` | enum | `MARKETVALUE`, `EXECUTIEWAARDE`, `MODELMATIG` (AVM). |
| `woz_waarde` | float | Municipal tax value — annual, lagged ~18 months. |
| `woz_reference_date` | date | Reference date for WOZ. |
| `property_value_current` | float | Indexed via CBS/Kadaster house-price index off `taxatie_waarde`. |
| `pc6` | str | NL 6-char postcode (e.g. `1011AB`) — granular concentration. |
| `gemeente` | str | Municipality. |
| `property_type` | enum | `APPARTEMENT`, `TUSSENWONING`, `HOEKWONING`, `2-ONDER-1-KAP`, `VRIJSTAAND`. |
| `bouwjaar` | int | Construction year — drives energy-label realism. |
| `energy_label` | enum | `A++++` … `G`. DNB climate-stress input; pricing differential now real. |
| `nhg_flag` | bool | NHG guarantee active. |
| `nhg_cap_at_origination` | float | Year-of-origination cap (€450k 2025, €435k 2024, €405k 2023…). |
| `nhg_premium_paid` | float | 0.4% (2025) of loan amount, paid by borrower. |
| `current_ltv` | derived | `current_balance / property_value_current`. Primary LGD driver. |
| `original_lti` | derived | `original_principal / gross_household_income`. Regulated cap. |

### Credit-risk metrics (Basel + IFRS 9)

| Field | Type | Why it matters |
|---|---|---|
| `pd_12m` | float [0,1] | 12-month PD (IFRS 9 Stage 1 ECL). |
| `pd_lifetime` | float [0,1] | Lifetime PD (Stages 2 & 3). |
| `lgd` | float [0,1] | LGD post-collateral, post-cost. Near-zero up to NHG cap. |
| `ead` | float | Exposure at default ≈ current balance for amortizing. |
| `ifrs9_stage` | enum (`1`, `2`, `3`) | Stage 1 = performing; 2 = SICR; 3 = credit-impaired. |
| `sicr_trigger_reason` | enum | See SICR section below. |
| `days_past_due` | int | Drives Stage 3 backstop (≥ 90 dpd). |
| `arrears_bucket` | enum | `0`, `1-30`, `31-60`, `61-90`, `90+`. |
| `restructured_flag` | bool | Forbearance → Stage 2 trigger. |
| `risk_weight` | float | Basel risk weight (IRB vs SA). NHG-backed loans drop materially. |
| `expected_loss` | derived | `pd × lgd × ead`. |

### Borrower affordability (Nibud / *Tijdelijke regeling*)

| Field | Type | Why it matters |
|---|---|---|
| `gross_household_income` | float | Used for LTI. |
| `partner_income_included` | bool | NL allows partner income in affordability. |
| `student_loan_debt` | float | DUO debt — affordability adjustment. |
| `bkr_score_band` | enum | `A`, `B`, `C`, `D`, `E` (Bureau Krediet Registratie). |
| `bkr_negative_registration_flag` | bool | A-coding present. |
| `dscr` | float | Income / debt service. |

## Synthetic generation strategy

The synthetic tape is what makes the demo credible. Key correlations:

- ~10,000 loans across vintages 2010 → 2025.
- **Vintage-correlated** product mix: pre-2013 skews `AFLOSSINGSVRIJ`/`SPAAR`; post-2013 dominantly `ANNUITEIT`.
- **Geo realism**: PC6 → CBS gemeente mapping; Randstad postcodes get higher prices, larger loans.
- **Energy label** distribution skewed by `bouwjaar` (pre-1992 stock dominantly C-G; post-2015 mostly A/A+).
- **Rate-fix cohorts**: ~25% of book has `rentevast_einddatum` in 2025–2028 (the reset wave).
- **Seeded easter eggs** for anomaly / validation testing:
  1. A vintage cohort with abnormally high `AFLOSSINGSVRIJ` share.
  2. A PC4 cluster with `taxatie_date` > 3 years stale.
  3. A small batch with `nhg_flag=True` but `original_principal > nhg_cap_at_origination`.
  4. A cluster with `interest_only_portion > 0.5 × property_value_at_origination`.

Deterministic seed; pure-function generator; tests pin output hash.

## IFRS 9 SICR triggers — NL-tuned

Dutch banks' SICR (Significant Increase in Credit Risk → Stage 2) policies are tighter than the IFRS 9 baseline. Implementation mirrors typical NL retail-bank policy:

| Trigger | Rule | Source |
|---|---|---|
| **Quantitative PD increase** | `pd_lifetime / pd_lifetime_at_origination > 2.5×` AND uplift > 0.5pp | EBA GL/2017/06 + NL practice |
| **30 dpd backstop** | `days_past_due ≥ 30` | IFRS 9 par. 5.5.11 (rebuttable; NL banks generally do not rebut) |
| **Forbearance** | `restructured_flag == True` for ≤ 24 months | EBA forbearance definition |
| **Watch list** | Manual qualitative flag | Internal credit policy |
| **Macro overlay** | DNB-mandated overlay on cohorts with `rentevast_einddatum` within 12 months AND `dscr < 1.2` | DNB 2024 sectoral guidance |
| **Climate transition** | `energy_label in {E, F, G}` AND `bouwjaar < 1992` — soft Stage-2 indicator | DNB climate risk guidance |

Stage 3 backstop: `days_past_due ≥ 90` OR `unlikely_to_pay_flag`.

## See also

- `docs/regulation-map.md` — full regulation citations
- `docs/governance/model-inventory.md` — every quantitative rule, owner, version
- `docs/appendix/anacredit-mapping.md` — AnaCredit attribute crosswalk
