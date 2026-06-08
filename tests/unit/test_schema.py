"""Schema tests — RED first per the TDD discipline in .claude/CLAUDE.md.

Covers every dimension of the Dutch mortgage loan-tape contract:
- Enum membership for all categorical fields (NL-specific values)
- Range / type constraints on numeric and date fields
- Cross-field invariants enforced at construction time
- Derived (computed) fields
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from loan_tape.schema import (
    ArrearsBucket,
    BkrScoreBand,
    BorrowerType,
    EnergyLabel,
    IFRS9Stage,
    Loan,
    PropertyType,
    RateType,
    RepaymentType,
    SicrTrigger,
    TaxatieType,
)


# ---------------------------------------------------------------------------
# Helper — minimum-viable Loan kwargs so individual tests can override one field
# ---------------------------------------------------------------------------


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "loan_id": "LN-0000001",
        "borrower_id": "BO-000001",
        "borrower_type": BorrowerType.DOORSTROMER,
        "origination_date": date(2018, 6, 1),
        "maturity_date": date(2048, 6, 1),
        "original_principal": 300_000.0,
        "current_balance": 250_000.0,
        "interest_rate": 0.025,
        "rate_type": RateType.RENTEVAST_10J,
        "rentevast_einddatum": date(2028, 6, 1),
        "repayment_type": RepaymentType.ANNUITEIT,
        "tax_deduction_eligible": True,
        "hra_phase_out_rate": 0.3697,
        "interest_only_portion": 0.0,
        "currency": "EUR",
        "property_value_at_origination": 350_000.0,
        "taxatie_waarde": 350_000.0,
        "taxatie_date": date(2018, 5, 1),
        "taxatie_type": TaxatieType.MARKETVALUE,
        "woz_waarde": 340_000.0,
        "woz_reference_date": date(2024, 1, 1),
        "property_value_current": 420_000.0,
        "pc6": "1011AB",
        "gemeente": "Amsterdam",
        "property_type": PropertyType.APPARTEMENT,
        "bouwjaar": 1995,
        "energy_label": EnergyLabel.B,
        "nhg_flag": False,
        "nhg_cap_at_origination": 265_000.0,
        "nhg_premium_paid": 0.0,
        "pd_12m": 0.005,
        "pd_lifetime": 0.04,
        "lgd": 0.15,
        "ead": 250_000.0,
        "ifrs9_stage": IFRS9Stage.ONE,
        "sicr_trigger_reason": SicrTrigger.NONE,
        "days_past_due": 0,
        "arrears_bucket": ArrearsBucket.ZERO,
        "restructured_flag": False,
        "watchlist_flag": False,
        "unlikely_to_pay_flag": False,
        "risk_weight": 0.35,
        "gross_household_income": 75_000.0,
        "partner_income_included": False,
        "student_loan_debt": 0.0,
        "bkr_score_band": BkrScoreBand.A,
        "bkr_negative_registration_flag": False,
        "dscr": 1.8,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Enum membership
# ---------------------------------------------------------------------------


def test_rate_type_enum_has_nl_values() -> None:
    """Dutch rate types — variable plus 4 fixed-rate periods."""
    values = {m.value for m in RateType}
    assert values == {
        "VARIABEL",
        "RENTEVAST_5J",
        "RENTEVAST_10J",
        "RENTEVAST_20J",
        "RENTEVAST_30J",
    }


def test_repayment_type_enum_has_nl_products() -> None:
    """NL-specific mortgage product set."""
    values = {m.value for m in RepaymentType}
    assert values == {
        "ANNUITEIT",
        "LINEAIR",
        "AFLOSSINGSVRIJ",
        "BANKSPAAR",
        "SPAAR",
        "BELEGGING",
        "HYBRIDE",
    }


def test_property_type_enum_has_nl_dwelling_types() -> None:
    values = {m.value for m in PropertyType}
    assert values == {
        "APPARTEMENT",
        "TUSSENWONING",
        "HOEKWONING",
        "2-ONDER-1-KAP",
        "VRIJSTAAND",
    }


def test_borrower_type_enum_has_nibud_cohorts() -> None:
    values = {m.value for m in BorrowerType}
    assert values == {"STARTER", "DOORSTROMER", "OUDERE"}


def test_energy_label_enum_covers_a_through_g_with_pluses() -> None:
    """Dutch energy labels — A++++ through G."""
    values = {m.value for m in EnergyLabel}
    expected = {"A++++", "A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G"}
    assert expected <= values


def test_ifrs9_stage_enum_has_three_stages() -> None:
    assert {m.value for m in IFRS9Stage} == {"1", "2", "3"}


def test_arrears_bucket_enum_has_standard_buckets() -> None:
    values = {m.value for m in ArrearsBucket}
    assert values == {"0", "1-30", "31-60", "61-90", "90+"}


def test_sicr_trigger_enum_covers_six_nl_triggers_plus_none() -> None:
    """Six NL-tuned SICR triggers from §2.6 plus a sentinel."""
    values = {m.value for m in SicrTrigger}
    assert {
        "NONE",
        "QUANT_PD_INCREASE",
        "DPD_30_BACKSTOP",
        "FORBEARANCE",
        "WATCHLIST",
        "MACRO_OVERLAY",
        "CLIMATE_TRANSITION",
    } <= values


# ---------------------------------------------------------------------------
# Construction — happy path
# ---------------------------------------------------------------------------


def test_loan_constructs_with_minimal_valid_kwargs() -> None:
    """The helper produces a valid loan that round-trips through the schema."""
    loan = Loan(**_kwargs())
    assert loan.loan_id == "LN-0000001"
    assert loan.currency == "EUR"
    assert loan.ifrs9_stage == IFRS9Stage.ONE


# ---------------------------------------------------------------------------
# Range / type constraints
# ---------------------------------------------------------------------------


def test_pd_12m_must_be_probability() -> None:
    with pytest.raises(ValidationError):
        Loan(**_kwargs(pd_12m=1.5))
    with pytest.raises(ValidationError):
        Loan(**_kwargs(pd_12m=-0.1))


def test_lgd_must_be_probability() -> None:
    with pytest.raises(ValidationError):
        Loan(**_kwargs(lgd=1.2))
    with pytest.raises(ValidationError):
        Loan(**_kwargs(lgd=-0.01))


def test_interest_rate_must_be_non_negative_and_below_one() -> None:
    """Decimal form — 0.025 == 2.5%. > 1.0 means somebody passed percent."""
    with pytest.raises(ValidationError):
        Loan(**_kwargs(interest_rate=2.5))  # likely passed % by mistake
    with pytest.raises(ValidationError):
        Loan(**_kwargs(interest_rate=-0.001))


def test_currency_is_eur_only() -> None:
    """This is a Dutch retail-mortgage tape; FX = nil."""
    with pytest.raises(ValidationError):
        Loan(**_kwargs(currency="USD"))


def test_days_past_due_non_negative_int() -> None:
    with pytest.raises(ValidationError):
        Loan(**_kwargs(days_past_due=-1))


def test_pc6_must_be_4digits_2letters() -> None:
    """NL 6-char postcode format: 4 digits + 2 uppercase letters."""
    with pytest.raises(ValidationError):
        Loan(**_kwargs(pc6="1011A"))  # too short
    with pytest.raises(ValidationError):
        Loan(**_kwargs(pc6="1011ab"))  # lowercase
    with pytest.raises(ValidationError):
        Loan(**_kwargs(pc6="ABCDEF"))  # no digits


def test_bouwjaar_in_plausible_range() -> None:
    with pytest.raises(ValidationError):
        Loan(**_kwargs(bouwjaar=1500))
    with pytest.raises(ValidationError):
        Loan(**_kwargs(bouwjaar=2200))


# ---------------------------------------------------------------------------
# Cross-field invariants (schema-level — not the full validation engine)
# ---------------------------------------------------------------------------


def test_maturity_after_origination() -> None:
    with pytest.raises(ValidationError):
        Loan(
            **_kwargs(
                origination_date=date(2020, 1, 1),
                maturity_date=date(2018, 1, 1),
            )
        )


def test_pd_lifetime_ge_pd_12m() -> None:
    """Lifetime PD must be at least the 12-month PD."""
    with pytest.raises(ValidationError):
        Loan(**_kwargs(pd_12m=0.05, pd_lifetime=0.03))


def test_stage_3_requires_dpd90_or_utp() -> None:
    """IFRS 9 backstop: Stage 3 implies dpd >= 90 OR unlikely_to_pay_flag."""
    with pytest.raises(ValidationError):
        Loan(
            **_kwargs(
                ifrs9_stage=IFRS9Stage.THREE,
                days_past_due=10,
                unlikely_to_pay_flag=False,
                restructured_flag=False,
            )
        )
    # OK: dpd ≥ 90
    Loan(
        **_kwargs(
            ifrs9_stage=IFRS9Stage.THREE,
            days_past_due=120,
            arrears_bucket=ArrearsBucket.NINETY_PLUS,
        )
    )
    # OK: UTP flag
    Loan(
        **_kwargs(
            ifrs9_stage=IFRS9Stage.THREE,
            days_past_due=0,
            unlikely_to_pay_flag=True,
            arrears_bucket=ArrearsBucket.ZERO,
        )
    )


def test_hra_eligibility_requires_post_2013_annuity_or_linear() -> None:
    """tax_deduction_eligible=True requires ANNUITEIT/LINEAIR post-2013."""
    # Wrong product type
    with pytest.raises(ValidationError):
        Loan(
            **_kwargs(
                tax_deduction_eligible=True,
                repayment_type=RepaymentType.AFLOSSINGSVRIJ,
            )
        )
    # Pre-2013 origination
    with pytest.raises(ValidationError):
        Loan(
            **_kwargs(
                tax_deduction_eligible=True,
                origination_date=date(2012, 12, 31),
            )
        )


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------


def test_current_ltv_derived_from_balance_and_value() -> None:
    loan = Loan(
        **_kwargs(
            current_balance=210_000.0,
            property_value_current=420_000.0,
        )
    )
    assert loan.current_ltv == pytest.approx(0.5)


def test_original_lti_derived_from_principal_and_income() -> None:
    loan = Loan(
        **_kwargs(
            original_principal=300_000.0,
            gross_household_income=75_000.0,
        )
    )
    assert loan.original_lti == pytest.approx(4.0)


def test_expected_loss_derived_pd_times_lgd_times_ead() -> None:
    """Stage 1: EL = pd_12m × lgd × ead. Stage 2/3: lifetime PD."""
    s1 = Loan(
        **_kwargs(
            ifrs9_stage=IFRS9Stage.ONE,
            pd_12m=0.01,
            lgd=0.20,
            ead=200_000.0,
        )
    )
    assert s1.expected_loss == pytest.approx(0.01 * 0.20 * 200_000.0)

    s2 = Loan(
        **_kwargs(
            ifrs9_stage=IFRS9Stage.TWO,
            pd_12m=0.01,
            pd_lifetime=0.08,
            lgd=0.20,
            ead=200_000.0,
            sicr_trigger_reason=SicrTrigger.QUANT_PD_INCREASE,
        )
    )
    assert s2.expected_loss == pytest.approx(0.08 * 0.20 * 200_000.0)
