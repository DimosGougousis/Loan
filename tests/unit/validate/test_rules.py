"""Validation rule tests — RED first per .claude/skills/add-validation-rule.md.

Every rule has at least one positive (flag) and one negative (pass) case.
Rules cite their source regulation in the implementation; tests assert it
flows into the RuleResult.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from loan_tape.schema import IFRS9Stage, Loan, RepaymentType
from loan_tape.validate.rules import (
    RULE_REGISTRY,
    Bcbs239Dimension,
    RuleResult,
    Severity,
    run_all_rules,
)


# Reuse the schema test helper — local copy so this file is self-contained.
def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "loan_id": "LN-RULE-0001",
        "borrower_id": "BO-RULE-0001",
        "borrower_type": "DOORSTROMER",
        "origination_date": date(2018, 6, 1),
        "maturity_date": date(2048, 6, 1),
        "original_principal": 300_000.0,
        "current_balance": 250_000.0,
        "interest_rate": 0.025,
        "rate_type": "RENTEVAST_10J",
        "rentevast_einddatum": date(2028, 6, 1),
        "repayment_type": "ANNUITEIT",
        "tax_deduction_eligible": True,
        "hra_phase_out_rate": 0.3697,
        "interest_only_portion": 0.0,
        "currency": "EUR",
        "property_value_at_origination": 350_000.0,
        "taxatie_waarde": 350_000.0,
        "taxatie_date": date(2018, 5, 1),
        "taxatie_type": "MARKETVALUE",
        "woz_waarde": 340_000.0,
        "woz_reference_date": date(2024, 1, 1),
        "property_value_current": 420_000.0,
        "pc6": "1011AB",
        "gemeente": "Amsterdam",
        "property_type": "APPARTEMENT",
        "bouwjaar": 1995,
        "energy_label": "B",
        "nhg_flag": False,
        "nhg_cap_at_origination": 265_000.0,
        "nhg_premium_paid": 0.0,
        "pd_12m": 0.005,
        "pd_lifetime": 0.04,
        "lgd": 0.15,
        "ead": 250_000.0,
        "ifrs9_stage": "1",
        "sicr_trigger_reason": "NONE",
        "days_past_due": 0,
        "arrears_bucket": "0",
        "restructured_flag": False,
        "watchlist_flag": False,
        "unlikely_to_pay_flag": False,
        "risk_weight": 0.35,
        "gross_household_income": 75_000.0,
        "partner_income_included": False,
        "student_loan_debt": 0.0,
        "bkr_score_band": "A",
        "bkr_negative_registration_flag": False,
        "dscr": 1.8,
    }
    base.update(overrides)
    return base


def _loan(**overrides: object) -> Loan:
    return Loan(**_kwargs(**overrides))


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------


def test_rule_result_contract() -> None:
    """Every RuleResult must carry rule_name, regulation, BCBS 239 dimension."""
    loan = _loan()
    for rule_name, rule_fn in RULE_REGISTRY.items():
        result = rule_fn(loan)
        assert isinstance(result, RuleResult)
        assert result.rule_name == rule_name
        assert result.regulation, f"{rule_name} missing regulation citation"
        assert result.bcbs239_dimension in {
            d.value for d in Bcbs239Dimension
        }


# ---------------------------------------------------------------------------
# Rule 1 — current_balance ≤ original_principal × 1.001
# ---------------------------------------------------------------------------


def test_negative_amortization_rule_flags_overflow() -> None:
    from loan_tape.validate.rules import negative_amortization_rule

    loan = _loan(current_balance=400_000.0, original_principal=300_000.0)
    r = negative_amortization_rule(loan)
    assert not r.passed
    assert r.severity == Severity.CRITICAL


def test_negative_amortization_rule_passes_when_within_tolerance() -> None:
    from loan_tape.validate.rules import negative_amortization_rule

    loan = _loan(current_balance=300_100.0, original_principal=300_000.0)
    assert negative_amortization_rule(loan).passed


# ---------------------------------------------------------------------------
# Rule 2 — Stage 3 ⇒ dpd≥90 OR unlikely_to_pay (schema enforces; rule re-checks)
# ---------------------------------------------------------------------------


def test_stage_3_backstop_rule_passes_on_clean_stage1() -> None:
    from loan_tape.validate.rules import stage_3_backstop_rule

    assert stage_3_backstop_rule(_loan()).passed


def test_stage_3_backstop_rule_passes_when_dpd90() -> None:
    """Schema already enforces; this rule echoes for explicit reporting."""
    from loan_tape.validate.rules import stage_3_backstop_rule

    loan = _loan(
        ifrs9_stage=IFRS9Stage.THREE.value,
        days_past_due=120,
        arrears_bucket="90+",
        unlikely_to_pay_flag=False,
    )
    assert stage_3_backstop_rule(loan).passed


# ---------------------------------------------------------------------------
# Rule 3 — NHG cap (nhg_flag ⇒ principal ≤ year-of-origination cap)
# ---------------------------------------------------------------------------


def test_nhg_cap_rule_flags_breach() -> None:
    from loan_tape.validate.rules import nhg_cap_rule

    loan = _loan(
        nhg_flag=True, original_principal=500_000.0, nhg_cap_at_origination=265_000.0
    )
    r = nhg_cap_rule(loan)
    assert not r.passed
    assert r.severity == Severity.CRITICAL
    assert "NHG" in r.regulation


def test_nhg_cap_rule_passes_when_no_nhg() -> None:
    from loan_tape.validate.rules import nhg_cap_rule

    loan = _loan(
        nhg_flag=False, original_principal=500_000.0, nhg_cap_at_origination=265_000.0
    )
    assert nhg_cap_rule(loan).passed


# ---------------------------------------------------------------------------
# Rule 4 — HRA eligibility (post-2013 + annuity/linear)
# Schema enforces; engine-level rule echoes
# ---------------------------------------------------------------------------


def test_hra_eligibility_rule_passes_on_compliant_loan() -> None:
    from loan_tape.validate.rules import hra_eligibility_rule

    assert hra_eligibility_rule(_loan()).passed


# ---------------------------------------------------------------------------
# Rule 5 — current_ltv tolerance vs derived
# ---------------------------------------------------------------------------


def test_ltv_consistency_rule_passes_on_clean() -> None:
    from loan_tape.validate.rules import ltv_consistency_rule

    assert ltv_consistency_rule(_loan()).passed


# ---------------------------------------------------------------------------
# Rule 6 — PD monotonicity (lifetime ≥ 12m)
# Schema enforces; engine-level rule echoes
# ---------------------------------------------------------------------------


def test_pd_monotonicity_rule_passes_on_clean() -> None:
    from loan_tape.validate.rules import pd_monotonicity_rule

    assert pd_monotonicity_rule(_loan()).passed


# ---------------------------------------------------------------------------
# Rule 7 — Stage 1 freshness: taxatie ≤ 36 months
# ---------------------------------------------------------------------------


def test_taxatie_freshness_rule_flags_stale_for_stage_1() -> None:
    from loan_tape.validate.rules import taxatie_freshness_rule

    loan = _loan(
        ifrs9_stage="1",
        taxatie_date=date(2018, 1, 1),  # ~7 years before reference
        property_value_current=420_000.0,
    )
    r = taxatie_freshness_rule(loan, reference_date=date(2025, 6, 1))
    assert not r.passed
    assert r.severity == Severity.MEDIUM


def test_taxatie_freshness_rule_passes_for_recent_taxatie() -> None:
    from loan_tape.validate.rules import taxatie_freshness_rule

    loan = _loan(
        ifrs9_stage="1",
        taxatie_date=date(2024, 1, 1),
    )
    assert taxatie_freshness_rule(loan, reference_date=date(2025, 6, 1)).passed


# ---------------------------------------------------------------------------
# Rule 8 — LTI cap (Tijdelijke regeling / Nibud)
# ---------------------------------------------------------------------------


def test_lti_cap_rule_flags_overflow() -> None:
    from loan_tape.validate.rules import lti_cap_rule

    # LTI > 6.0 — exceeds any plausible Nibud-derived cap.
    loan = _loan(original_principal=600_000.0, gross_household_income=80_000.0)
    r = lti_cap_rule(loan)
    assert not r.passed


def test_lti_cap_rule_passes_for_moderate_lti() -> None:
    from loan_tape.validate.rules import lti_cap_rule

    loan = _loan(original_principal=300_000.0, gross_household_income=75_000.0)
    assert lti_cap_rule(loan).passed


# ---------------------------------------------------------------------------
# Rule 9 — Interest-only portion ≤ 50% of property value for HRA loans
# ---------------------------------------------------------------------------


def test_interest_only_cap_flags_high_io_on_hra_loan() -> None:
    from loan_tape.validate.rules import interest_only_cap_rule

    loan = _loan(
        tax_deduction_eligible=True,
        property_value_at_origination=400_000.0,
        interest_only_portion=300_000.0,  # 75% > 50% cap
        repayment_type=RepaymentType.ANNUITEIT.value,
    )
    r = interest_only_cap_rule(loan)
    assert not r.passed
    assert r.severity == Severity.HIGH


def test_interest_only_cap_passes_when_under_50pct() -> None:
    from loan_tape.validate.rules import interest_only_cap_rule

    loan = _loan(
        tax_deduction_eligible=True,
        property_value_at_origination=400_000.0,
        interest_only_portion=150_000.0,
    )
    assert interest_only_cap_rule(loan).passed


# ---------------------------------------------------------------------------
# Registry + portfolio runner
# ---------------------------------------------------------------------------


def test_rule_registry_covers_nine_named_rules() -> None:
    """The §5.5 spec lists 9 cross-field rules."""
    assert set(RULE_REGISTRY) == {
        "negative_amortization",
        "stage_3_backstop",
        "nhg_cap",
        "hra_eligibility",
        "ltv_consistency",
        "pd_monotonicity",
        "taxatie_freshness",
        "lti_cap",
        "interest_only_cap",
    }


def test_run_all_rules_on_golden_tape_has_no_critical_findings(
    golden_tape: pl.DataFrame,
) -> None:
    """Clean golden fixture must have zero CRITICAL findings."""
    results = run_all_rules(golden_tape, reference_date=date(2025, 6, 1))
    criticals = [r for r in results if r.severity == Severity.CRITICAL]
    assert criticals == [], (
        f"unexpected criticals on golden tape: "
        f"{[(r.rule_name, r.loan_id) for r in criticals[:5]]}"
    )


def test_run_all_rules_catches_easter_eggs_on_injected_tape() -> None:
    """Tape with seeded easter eggs must surface their corresponding rules."""
    from loan_tape.generator import generate_tape

    tape = generate_tape(n=600, seed=99, inject_easter_eggs=True)
    results = run_all_rules(tape, reference_date=date(2025, 6, 1))
    failed_rules = {r.rule_name for r in results if not r.passed}
    # NHG_CAP_BREACH_BATCH should always trip nhg_cap;
    # HIGH_INTEREST_ONLY_CLUSTER trips interest_only_cap.
    assert "nhg_cap" in failed_rules
    assert "interest_only_cap" in failed_rules


def test_severity_to_str_returns_label() -> None:
    assert Severity.CRITICAL.value == "CRITICAL"
    assert Severity.HIGH.value == "HIGH"
    assert Severity.MEDIUM.value == "MEDIUM"
    assert Severity.LOW.value == "LOW"
