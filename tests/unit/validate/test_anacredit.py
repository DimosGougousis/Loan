"""AnaCredit attribute mapper tests — ECB Reg 2016/867 conformance (RED first)."""

from __future__ import annotations

from datetime import date

import polars as pl

from loan_tape.schema import (
    ArrearsBucket,
    IFRS9Stage,
    Loan,
    PropertyType,
    RateType,
    RepaymentType,
    TaxatieType,
)
from loan_tape.validate.anacredit import (
    REQUIRED_ATTRIBUTES,
    AnaCreditAttribute,
    ConformanceResult,
    check_conformance,
    map_loan,
    portfolio_conformance,
)


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "loan_id": "LN-AC-0001",
        "borrower_id": "BO-AC-0001",
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
        "nhg_flag": True,
        "nhg_cap_at_origination": 265_000.0,
        "nhg_premium_paid": 1325.0,
        "pd_12m": 0.005,
        "pd_lifetime": 0.04,
        "lgd": 0.02,
        "ead": 250_000.0,
        "ifrs9_stage": "1",
        "sicr_trigger_reason": "NONE",
        "days_past_due": 0,
        "arrears_bucket": "0",
        "restructured_flag": False,
        "watchlist_flag": False,
        "unlikely_to_pay_flag": False,
        "risk_weight": 0.08,
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
# Direct attribute mappings
# ---------------------------------------------------------------------------


def test_map_loan_returns_required_attributes() -> None:
    """Every required AnaCredit attribute is present in the mapper output."""
    out = map_loan(_loan())
    for attr in REQUIRED_ATTRIBUTES:
        assert attr in out, f"required attribute missing: {attr}"


def test_contract_and_counterparty_identifiers() -> None:
    loan = _loan()
    out = map_loan(loan)
    assert out[AnaCreditAttribute.CONTRACT_IDENTIFIER] == loan.loan_id
    assert out[AnaCreditAttribute.COUNTERPARTY_IDENTIFIER] == loan.borrower_id


def test_currency_passthrough() -> None:
    out = map_loan(_loan())
    assert out[AnaCreditAttribute.CURRENCY] == "EUR"


def test_dates_map_directly() -> None:
    loan = _loan()
    out = map_loan(loan)
    assert out[AnaCreditAttribute.INCEPTION_DATE] == loan.origination_date
    assert out[AnaCreditAttribute.SETTLEMENT_DATE] == loan.origination_date
    assert out[AnaCreditAttribute.LEGAL_FINAL_MATURITY] == loan.maturity_date


def test_amounts_map_directly() -> None:
    loan = _loan()
    out = map_loan(loan)
    assert out[AnaCreditAttribute.OUTSTANDING_NOMINAL] == loan.current_balance
    assert out[AnaCreditAttribute.COMMITMENT_AT_INCEPTION] == loan.original_principal


def test_credit_risk_metrics_pass_through() -> None:
    loan = _loan()
    out = map_loan(loan)
    assert out[AnaCreditAttribute.PROBABILITY_OF_DEFAULT_12M] == loan.pd_12m
    assert out[AnaCreditAttribute.PROBABILITY_OF_DEFAULT_LIFETIME] == loan.pd_lifetime
    assert out[AnaCreditAttribute.LOSS_GIVEN_DEFAULT] == loan.lgd
    assert out[AnaCreditAttribute.EXPOSURE_AT_DEFAULT] == loan.ead


# ---------------------------------------------------------------------------
# Derived attributes
# ---------------------------------------------------------------------------


def test_type_of_instrument_is_mortgage() -> None:
    out = map_loan(_loan())
    assert out[AnaCreditAttribute.TYPE_OF_INSTRUMENT] == "Mortgage loan"


def test_country_is_nl() -> None:
    out = map_loan(_loan())
    assert out[AnaCreditAttribute.REAL_ESTATE_COUNTRY] == "NL"


def test_type_of_interest_rate_fixed_for_rentevast() -> None:
    out = map_loan(_loan(rate_type=RateType.RENTEVAST_10J.value))
    assert out[AnaCreditAttribute.TYPE_OF_INTEREST_RATE] == "Fixed"


def test_type_of_interest_rate_variable_for_variabel() -> None:
    out = map_loan(_loan(rate_type=RateType.VARIABEL.value))
    assert out[AnaCreditAttribute.TYPE_OF_INTEREST_RATE] == "Variable"


def test_performing_status_derived_from_stage_and_arrears() -> None:
    perf = _loan(ifrs9_stage=IFRS9Stage.ONE.value, arrears_bucket=ArrearsBucket.ZERO.value)
    npe = _loan(
        ifrs9_stage=IFRS9Stage.THREE.value,
        days_past_due=120,
        arrears_bucket=ArrearsBucket.NINETY_PLUS.value,
        unlikely_to_pay_flag=True,
    )
    assert map_loan(perf)[AnaCreditAttribute.PERFORMING_STATUS] == "Performing"
    assert map_loan(npe)[AnaCreditAttribute.PERFORMING_STATUS] == "Non-performing"


def test_default_status_derived_from_stage_3() -> None:
    perf = _loan(ifrs9_stage=IFRS9Stage.ONE.value)
    default = _loan(
        ifrs9_stage=IFRS9Stage.THREE.value,
        days_past_due=120,
        arrears_bucket=ArrearsBucket.NINETY_PLUS.value,
    )
    assert map_loan(perf)[AnaCreditAttribute.DEFAULT_STATUS] == "Not in default"
    assert map_loan(default)[AnaCreditAttribute.DEFAULT_STATUS] == "Default"


def test_type_of_protection_includes_nhg_when_flagged() -> None:
    nhg = _loan(nhg_flag=True)
    no_nhg = _loan(nhg_flag=False)
    assert "NHG guarantee" in map_loan(nhg)[AnaCreditAttribute.TYPE_OF_PROTECTION]
    assert "NHG guarantee" not in map_loan(no_nhg)[AnaCreditAttribute.TYPE_OF_PROTECTION]


def test_type_of_protection_value_translates_taxatie_type() -> None:
    market = _loan(taxatie_type=TaxatieType.MARKETVALUE.value)
    foreclosure = _loan(taxatie_type=TaxatieType.EXECUTIEWAARDE.value)
    avm = _loan(taxatie_type=TaxatieType.MODELMATIG.value)
    assert map_loan(market)[AnaCreditAttribute.TYPE_OF_PROTECTION_VALUE] == "Market value"
    assert (
        map_loan(foreclosure)[AnaCreditAttribute.TYPE_OF_PROTECTION_VALUE]
        == "Notional amount"
    )
    assert map_loan(avm)[AnaCreditAttribute.TYPE_OF_PROTECTION_VALUE] == "Other"


def test_ltv_at_origination_derived() -> None:
    loan = _loan(original_principal=300_000.0, property_value_at_origination=400_000.0)
    out = map_loan(loan)
    assert out[AnaCreditAttribute.LTV_AT_ORIGINATION] == 0.75


def test_forbearance_status_translates() -> None:
    fb = _loan(restructured_flag=True)
    no_fb = _loan(restructured_flag=False)
    assert map_loan(fb)[AnaCreditAttribute.FORBEARANCE_STATUS] == "Forborne"
    assert map_loan(no_fb)[AnaCreditAttribute.FORBEARANCE_STATUS] == "Not forborne"


# ---------------------------------------------------------------------------
# Conformance check
# ---------------------------------------------------------------------------


def test_check_conformance_passes_on_clean_loan() -> None:
    result = check_conformance(_loan())
    assert isinstance(result, ConformanceResult)
    assert result.populated
    assert result.enumerated
    assert result.missing_attributes == []
    assert result.invalid_values == []


def test_check_conformance_flags_invalid_currency() -> None:
    """Conformance detects out-of-enumeration values even if schema let them slip."""
    out = map_loan(_loan())
    # Simulate a downstream tamper.
    out[AnaCreditAttribute.CURRENCY] = "XYZ"
    result = check_conformance(_loan(), precomputed=out)
    assert not result.enumerated
    assert any("currency" in v.lower() for v in result.invalid_values)


def test_check_conformance_flags_missing_required() -> None:
    out = map_loan(_loan())
    del out[AnaCreditAttribute.OUTSTANDING_NOMINAL]
    result = check_conformance(_loan(), precomputed=out)
    assert not result.populated
    assert AnaCreditAttribute.OUTSTANDING_NOMINAL in result.missing_attributes


def test_portfolio_conformance_returns_share(golden_tape: pl.DataFrame) -> None:
    """Clean golden tape must hit ≥ 98% conformance per the validation rubric."""
    share, results = portfolio_conformance(golden_tape)
    assert 0.0 <= share <= 1.0
    assert len(results) == golden_tape.shape[0]
    assert share >= 0.98, f"unexpected AnaCredit non-conformance: {share:.4f}"
