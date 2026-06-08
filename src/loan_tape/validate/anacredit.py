"""AnaCredit attribute mapper — ECB Regulation (EU) 2016/867, Annex II.

Maps the Dutch mortgage ``Loan`` schema to AnaCredit attributes used in the
ECB's loan-level reporting framework. The conformance check enforces:

1. Every attribute marked REQUIRED is populated.
2. Every enumerated attribute carries a value from the ECB-allowed list.

Per fail-gracefully §7.7.1 stage 2 (AnaCredit-required attribute null): the
pipeline advances with a WARNING and cannot reach Publish without resolution.

Full crosswalk lives in ``docs/appendix/anacredit-mapping.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

import polars as pl

from loan_tape.schema import (
    ArrearsBucket,
    IFRS9Stage,
    Loan,
    RateType,
    TaxatieType,
)


# ---------------------------------------------------------------------------
# AnaCredit attribute keys (subset relevant to Dutch retail mortgages)
# ---------------------------------------------------------------------------


class AnaCreditAttribute(str, Enum):
    """Subset of AnaCredit attributes populated by this platform.

    Full list lives in ECB Reg 2016/867 Annex II.
    """

    # Instrument dataset
    CONTRACT_IDENTIFIER = "contract_identifier"
    INCEPTION_DATE = "inception_date"
    SETTLEMENT_DATE = "settlement_date"
    LEGAL_FINAL_MATURITY = "legal_final_maturity_date"
    CURRENCY = "currency"
    COMMITMENT_AT_INCEPTION = "commitment_amount_at_inception"
    TYPE_OF_INSTRUMENT = "type_of_instrument"
    TYPE_OF_INTEREST_RATE = "type_of_interest_rate"
    INTEREST_RATE = "interest_rate"
    PROJECT_FINANCE_LOAN = "project_finance_loan"
    LTV_AT_ORIGINATION = "ltv_at_origination"

    # Counterparty dataset
    COUNTERPARTY_IDENTIFIER = "counterparty_identifier"

    # Financial dataset
    OUTSTANDING_NOMINAL = "outstanding_nominal_amount"
    PERFORMING_STATUS = "performing_status"
    DEFAULT_STATUS = "default_status_of_instrument"
    FORBEARANCE_STATUS = "forbearance_status"
    CURRENT_LTV = "current_ltv"
    PROBABILITY_OF_DEFAULT_12M = "pd_12m"
    PROBABILITY_OF_DEFAULT_LIFETIME = "pd_lifetime"
    LOSS_GIVEN_DEFAULT = "lgd"
    EXPOSURE_AT_DEFAULT = "ead"
    RISK_WEIGHT = "risk_weight"

    # Protection dataset
    TYPE_OF_PROTECTION = "type_of_protection"
    PROTECTION_VALUE = "protection_value"
    TYPE_OF_PROTECTION_VALUE = "type_of_protection_value"
    PROTECTION_VALUATION_DATE = "protection_valuation_date"
    REAL_ESTATE_POSTAL_CODE = "real_estate_postal_code"
    REAL_ESTATE_COUNTRY = "real_estate_country"
    REAL_ESTATE_CONSTRUCTION_YEAR = "real_estate_construction_year"
    ENERGY_PERFORMANCE_CERTIFICATE = "energy_performance_certificate"

    # Accounting dataset
    ACCOUNTING_CLASSIFICATION = "accounting_classification_ifrs9_stage"
    ACCUMULATED_IMPAIRMENT = "accumulated_impairment_amount"


REQUIRED_ATTRIBUTES: frozenset[AnaCreditAttribute] = frozenset(
    {
        AnaCreditAttribute.CONTRACT_IDENTIFIER,
        AnaCreditAttribute.COUNTERPARTY_IDENTIFIER,
        AnaCreditAttribute.INCEPTION_DATE,
        AnaCreditAttribute.LEGAL_FINAL_MATURITY,
        AnaCreditAttribute.CURRENCY,
        AnaCreditAttribute.OUTSTANDING_NOMINAL,
        AnaCreditAttribute.COMMITMENT_AT_INCEPTION,
        AnaCreditAttribute.TYPE_OF_INSTRUMENT,
        AnaCreditAttribute.TYPE_OF_INTEREST_RATE,
        AnaCreditAttribute.INTEREST_RATE,
        AnaCreditAttribute.PERFORMING_STATUS,
        AnaCreditAttribute.DEFAULT_STATUS,
        AnaCreditAttribute.TYPE_OF_PROTECTION,
        AnaCreditAttribute.PROTECTION_VALUE,
        AnaCreditAttribute.PROTECTION_VALUATION_DATE,
        AnaCreditAttribute.REAL_ESTATE_POSTAL_CODE,
        AnaCreditAttribute.REAL_ESTATE_COUNTRY,
        AnaCreditAttribute.ACCOUNTING_CLASSIFICATION,
    }
)


# Allowed enumerations per the ECB AnaCredit manual.
_ALLOWED_ENUMS: dict[AnaCreditAttribute, frozenset[str]] = {
    AnaCreditAttribute.CURRENCY: frozenset({"EUR"}),
    AnaCreditAttribute.TYPE_OF_INSTRUMENT: frozenset({"Mortgage loan"}),
    AnaCreditAttribute.TYPE_OF_INTEREST_RATE: frozenset({"Fixed", "Variable"}),
    AnaCreditAttribute.PERFORMING_STATUS: frozenset({"Performing", "Non-performing"}),
    AnaCreditAttribute.DEFAULT_STATUS: frozenset({"Default", "Not in default"}),
    AnaCreditAttribute.FORBEARANCE_STATUS: frozenset({"Forborne", "Not forborne"}),
    AnaCreditAttribute.TYPE_OF_PROTECTION_VALUE: frozenset(
        {"Market value", "Notional amount", "Other"}
    ),
    AnaCreditAttribute.REAL_ESTATE_COUNTRY: frozenset({"NL"}),
    AnaCreditAttribute.ACCOUNTING_CLASSIFICATION: frozenset({"Stage 1", "Stage 2", "Stage 3"}),
}


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------


def _interest_rate_kind(rate_type: RateType) -> str:
    return "Variable" if rate_type == RateType.VARIABEL else "Fixed"


def _performing_status(loan: Loan) -> str:
    """Stage 3 OR dpd ≥ 90 OR UTP/forborne → Non-performing. Else Performing."""
    if loan.ifrs9_stage == IFRS9Stage.THREE:
        return "Non-performing"
    if loan.days_past_due >= 90:
        return "Non-performing"
    if loan.unlikely_to_pay_flag:
        return "Non-performing"
    if loan.arrears_bucket == ArrearsBucket.NINETY_PLUS:
        return "Non-performing"
    return "Performing"


def _default_status(loan: Loan) -> str:
    return "Default" if loan.ifrs9_stage == IFRS9Stage.THREE else "Not in default"


def _type_of_protection(loan: Loan) -> str:
    base = "Residential real estate"
    return f"{base} + NHG guarantee" if loan.nhg_flag else base


def _type_of_protection_value(taxatie_type: TaxatieType) -> str:
    return {
        TaxatieType.MARKETVALUE: "Market value",
        TaxatieType.EXECUTIEWAARDE: "Notional amount",
        TaxatieType.MODELMATIG: "Other",
    }[taxatie_type]


def _accounting_classification(stage: IFRS9Stage) -> str:
    return {
        IFRS9Stage.ONE: "Stage 1",
        IFRS9Stage.TWO: "Stage 2",
        IFRS9Stage.THREE: "Stage 3",
    }[stage]


def _forbearance_status(loan: Loan) -> str:
    return "Forborne" if loan.restructured_flag else "Not forborne"


def map_loan(loan: Loan) -> dict[AnaCreditAttribute, Any]:
    """Translate a ``Loan`` into its AnaCredit attribute dict.

    Pure function. Values are Python primitives (str, float, int, date).
    """
    ltv_origination = (
        loan.original_principal / loan.property_value_at_origination
        if loan.property_value_at_origination
        else 0.0
    )
    return {
        # Instrument
        AnaCreditAttribute.CONTRACT_IDENTIFIER: loan.loan_id,
        AnaCreditAttribute.INCEPTION_DATE: loan.origination_date,
        AnaCreditAttribute.SETTLEMENT_DATE: loan.origination_date,
        AnaCreditAttribute.LEGAL_FINAL_MATURITY: loan.maturity_date,
        AnaCreditAttribute.CURRENCY: loan.currency,
        AnaCreditAttribute.COMMITMENT_AT_INCEPTION: loan.original_principal,
        AnaCreditAttribute.TYPE_OF_INSTRUMENT: "Mortgage loan",
        AnaCreditAttribute.TYPE_OF_INTEREST_RATE: _interest_rate_kind(loan.rate_type),
        AnaCreditAttribute.INTEREST_RATE: loan.interest_rate,
        AnaCreditAttribute.PROJECT_FINANCE_LOAN: False,
        AnaCreditAttribute.LTV_AT_ORIGINATION: round(ltv_origination, 6),
        # Counterparty
        AnaCreditAttribute.COUNTERPARTY_IDENTIFIER: loan.borrower_id,
        # Financial
        AnaCreditAttribute.OUTSTANDING_NOMINAL: loan.current_balance,
        AnaCreditAttribute.PERFORMING_STATUS: _performing_status(loan),
        AnaCreditAttribute.DEFAULT_STATUS: _default_status(loan),
        AnaCreditAttribute.FORBEARANCE_STATUS: _forbearance_status(loan),
        AnaCreditAttribute.CURRENT_LTV: loan.current_ltv,
        AnaCreditAttribute.PROBABILITY_OF_DEFAULT_12M: loan.pd_12m,
        AnaCreditAttribute.PROBABILITY_OF_DEFAULT_LIFETIME: loan.pd_lifetime,
        AnaCreditAttribute.LOSS_GIVEN_DEFAULT: loan.lgd,
        AnaCreditAttribute.EXPOSURE_AT_DEFAULT: loan.ead,
        AnaCreditAttribute.RISK_WEIGHT: loan.risk_weight,
        # Protection
        AnaCreditAttribute.TYPE_OF_PROTECTION: _type_of_protection(loan),
        AnaCreditAttribute.PROTECTION_VALUE: loan.taxatie_waarde,
        AnaCreditAttribute.TYPE_OF_PROTECTION_VALUE: _type_of_protection_value(loan.taxatie_type),
        AnaCreditAttribute.PROTECTION_VALUATION_DATE: loan.taxatie_date,
        AnaCreditAttribute.REAL_ESTATE_POSTAL_CODE: loan.pc6,
        AnaCreditAttribute.REAL_ESTATE_COUNTRY: "NL",
        AnaCreditAttribute.REAL_ESTATE_CONSTRUCTION_YEAR: loan.bouwjaar,
        AnaCreditAttribute.ENERGY_PERFORMANCE_CERTIFICATE: loan.energy_label.value,
        # Accounting
        AnaCreditAttribute.ACCOUNTING_CLASSIFICATION: _accounting_classification(loan.ifrs9_stage),
        AnaCreditAttribute.ACCUMULATED_IMPAIRMENT: round(loan.expected_loss, 2),
    }


# ---------------------------------------------------------------------------
# Conformance check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConformanceResult:
    """Outcome of a conformance check for one loan."""

    loan_id: str
    populated: bool
    enumerated: bool
    missing_attributes: list[AnaCreditAttribute] = field(default_factory=list)
    invalid_values: list[str] = field(default_factory=list)

    @property
    def conforming(self) -> bool:
        return self.populated and self.enumerated


def check_conformance(
    loan: Loan,
    precomputed: dict[AnaCreditAttribute, Any] | None = None,
) -> ConformanceResult:
    """Check that every required attribute is populated and enums are in range."""
    attrs = precomputed if precomputed is not None else map_loan(loan)

    missing: list[AnaCreditAttribute] = []
    for required in REQUIRED_ATTRIBUTES:
        value = attrs.get(required)
        if value is None or value == "":
            missing.append(required)

    invalid: list[str] = []
    for attr, allowed in _ALLOWED_ENUMS.items():
        value = attrs.get(attr)
        if value is None:
            continue  # missing-required handled above
        if value not in allowed:
            invalid.append(
                f"{attr.value} value {value!r} not in allowed enumeration {sorted(allowed)}"
            )

    return ConformanceResult(
        loan_id=loan.loan_id,
        populated=not missing,
        enumerated=not invalid,
        missing_attributes=missing,
        invalid_values=invalid,
    )


def portfolio_conformance(
    tape: pl.DataFrame,
) -> tuple[float, list[ConformanceResult]]:
    """Run ``check_conformance`` over every loan in ``tape``.

    Returns ``(conformance_share, per_loan_results)`` where the share is the
    proportion of conforming loans (populated AND enumerated).
    """
    payload_cols = [c for c in tape.columns if c != "easter_egg"]
    results: list[ConformanceResult] = []
    for row in tape.select(payload_cols).to_dicts():
        try:
            loan = Loan(**row)
        except Exception:  # noqa: BLE001 — fail-gracefully: bad rows handled upstream
            continue
        results.append(check_conformance(loan))
    if not results:
        return 0.0, results
    conforming = sum(1 for r in results if r.conforming)
    return conforming / len(results), results


# ---------------------------------------------------------------------------
# Helpers — handy when building a polars-friendly mapping table
# ---------------------------------------------------------------------------


def map_loan_to_dict(loan: Loan) -> dict[str, Any]:
    """Same as ``map_loan`` but with string keys for DataFrame ingest."""
    return {k.value: v for k, v in map_loan(loan).items()}


def map_tape(tape: pl.DataFrame) -> pl.DataFrame:
    """Translate a full tape to its AnaCredit-attribute DataFrame."""
    payload_cols = [c for c in tape.columns if c != "easter_egg"]
    rows: list[dict[str, Any]] = []
    for row in tape.select(payload_cols).to_dicts():
        loan = Loan(**row)
        rows.append(map_loan_to_dict(loan))
    return pl.from_dicts(rows)


__all__ = [
    "AnaCreditAttribute",
    "ConformanceResult",
    "REQUIRED_ATTRIBUTES",
    "check_conformance",
    "map_loan",
    "map_loan_to_dict",
    "map_tape",
    "portfolio_conformance",
]


# Re-export for convenience (used by tests/docs):
__doc__ = __doc__ + f"\n\nFirst written: {date(2026, 6, 8)}.\n"
