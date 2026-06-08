# Regulation Map

> Every quantitative rule in the platform is anchored to a regulation. This document is the mapping. Every interview question of the form *"why this threshold?"* should be answerable by clicking through to a row here.

## Map

| Regulation | Issuer | Where it shows up in the platform |
|---|---|---|
| **IFRS 9** (Financial Instruments) | IASB | `src/loan_tape/ecl/ifrs9.py` — staging logic, ECL = PD × LGD × EAD. Quick Scan IFRS 9 stage mix. |
| **IFRS 9 par. 5.5.11** (30-dpd rebuttable backstop) | IASB | `src/loan_tape/ecl/sicr.py::DPD_30_BACKSTOP` |
| **EBA GL/2017/06** (SICR guidelines) | EBA | `src/loan_tape/ecl/sicr.py::QUANT_PD_INCREASE` thresholds + forbearance trigger |
| **EBA forbearance definition** | EBA | `src/loan_tape/ecl/sicr.py::FORBEARANCE` trigger |
| **EBA stress-test methodology** | EBA | `src/loan_tape/analytics/stress.py` scenario structure mirrors EBA adverse-scenario pattern |
| **CRR III / Basel IV** | EU / BCBS | `risk_weight` field on every loan; RWA-density appears in Portfolio Analysis. NHG → lower risk weight. |
| **DNB Guidance on the use of AI (2024)** | DNB | `docs/governance/three-lines-of-defense.md` SAFEST mapping; `docs/eu-ai-act-position.md` |
| **DNB climate stress test methodology** | DNB | Stress scenario `energy_label_transition` in `src/loan_tape/analytics/stress.py`. SICR climate-transition soft trigger in `sicr.py`. |
| **DNB 2024 sectoral guidance (rentevast cohort)** | DNB | SICR `MACRO_OVERLAY` trigger in `sicr.py` |
| **BCBS 239** (Risk data aggregation) | BCBS | `src/loan_tape/validate/report.py` groups findings by BCBS 239 dimension (accuracy / completeness / timeliness / integrity). |
| **AnaCredit (ECB Reg 2016/867)** | ECB | `src/loan_tape/validate/anacredit.py` attribute crosswalk; `docs/appendix/anacredit-mapping.md` full table |
| **NHG / WEW rules** | Stichting WEW | `nhg_flag`, `nhg_cap_at_origination`, validation rule `nhg_cap_rule` in `validate/rules.py`. LGD floor on NHG-backed loans. |
| ***Tijdelijke regeling hypothecair krediet*** | Min. Fin. + AFM | Annual LTI/LTV caps; affordability validation rules. `data/reference/nibud_lti.csv` |
| **Nibud norms** | Nibud | LTI cap lookup in `data/reference/nibud_lti.csv`; affordability rule in `validate/rules.py` |
| **GDPR (AVG)** | EU | Synthetic data only → no PII → no DPIA. Stated in README and `docs/eu-ai-act-position.md`. |
| **EU AI Act (Reg 2024/1689)** | EU | `docs/eu-ai-act-position.md` — Articles 9, 10, 13, 14, 15 mapping. |
| **DORA (Reg 2022/2554)** | EU | `docs/eu-ai-act-position.md` DORA crosswalk. CI, dependency pinning, secrets scanning, change management. |

## How to add a regulation

When a new regulation is cited (in a new validation rule, SICR trigger, stress scenario, or compliance control):

1. Add a row to the table above.
2. Add the citation string to the rule/trigger/scenario in code (`regulation` field on `RuleResult` or docstring).
3. Update `docs/governance/model-inventory.md` with the new rule and its regulatory anchor.

## See also

- `docs/governance/model-inventory.md` — every quantitative rule
- `docs/eu-ai-act-position.md` — EU AI Act stance
- `docs/governance/three-lines-of-defense.md` — DNB SAFEST mapping
- `docs/domain-primer.md` — Dutch mortgage domain context
