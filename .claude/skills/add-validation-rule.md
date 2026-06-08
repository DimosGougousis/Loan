---
name: add-validation-rule
description: Add a new cross-field validation rule to the NL loan-tape validator. Use whenever a regulatory or schema rule must be enforced at ingest.
---

# Add a Validation Rule

## When to use

- A new NL regulation (e.g., updated Nibud LTI table, new NHG cap year) imposes a rule.
- A new schema field needs a cross-field check.
- BCBS 239 dimension (accuracy, completeness, timeliness, integrity) needs additional coverage.

## Procedure

1. **Write the failing test FIRST.** `tests/unit/validate/test_rules.py`:
   ```python
   def test_nhg_cap_rule_flags_overflow():
       loan = build_loan(nhg_flag=True, original_principal=500_000,
                         nhg_cap_at_origination=450_000)
       result = nhg_cap_rule(loan)
       assert not result.passed
       assert result.severity == Severity.CRITICAL
       assert "NHG cap" in result.message
   ```
   Run: fails because `nhg_cap_rule` doesn't exist.

2. **Implement in `src/loan_tape/validate/rules.py`.**
   ```python
   def nhg_cap_rule(loan: Loan) -> RuleResult:
       """NHG loans must not exceed the year-of-origination NHG cap.
       Source: WEW / Stichting Waarborgfonds Eigen Woningen — annual cap publication.
       """
       if loan.nhg_flag and loan.original_principal > loan.nhg_cap_at_origination:
           return RuleResult(
               passed=False,
               severity=Severity.CRITICAL,
               loan_id=loan.loan_id,
               message=f"NHG-flagged loan exceeds NHG cap: "
                       f"{loan.original_principal:,.0f} > {loan.nhg_cap_at_origination:,.0f}",
               rule_name="nhg_cap",
               regulation="NHG / WEW",
               bcbs239_dimension="integrity",
           )
       return RuleResult.passed_for(loan, rule_name="nhg_cap")
   ```

3. **Register in `RULE_REGISTRY`** at the bottom of `rules.py`.

4. **Run the test.** Confirm pass.

5. **Add to the easter-egg tape** (data/samples or evals/datasets) a loan that triggers the rule.

6. **Update the eval rubric** `evals/rubrics/validation_report.md` if the rule is part of the ≥95% recall target.

7. **Document in `docs/regulation-map.md`** with the source regulation.

## Rule contract

Every rule is a pure function `(loan: Loan) -> RuleResult` where `RuleResult` has:

- `passed: bool`
- `severity: Severity` (CRITICAL / HIGH / MEDIUM / LOW)
- `loan_id: str`
- `message: str` (human-readable, includes the offending values)
- `rule_name: str` (snake_case stable identifier)
- `regulation: str` (citation: "IFRS 9 par. 5.5.11", "EBA GL/2017/06", "NHG / WEW", "Tijdelijke regeling hypothecair krediet 2025", etc.)
- `bcbs239_dimension: str` (accuracy / completeness / timeliness / integrity)

## Severity guide

| Severity | When | Effect on pipeline |
|---|---|---|
| CRITICAL | Regulatory breach, hard schema violation | Blocks Publish stage; requires 1st-line override |
| HIGH | Data quality issue affecting EL calculation | Surfaces in report; does not block |
| MEDIUM | Freshness / completeness gap | Surfaces in report |
| LOW | Cosmetic or advisory | Surfaces in report |

## Checklist

- [ ] Failing test written first
- [ ] Rule is pure function `(loan) -> RuleResult`
- [ ] Regulation citation included
- [ ] BCBS 239 dimension assigned
- [ ] Registered in `RULE_REGISTRY`
- [ ] Easter-egg fixture triggers the rule
- [ ] Eval rubric updated if part of recall target
- [ ] `docs/regulation-map.md` updated
- [ ] `[ai-assisted]` commit
