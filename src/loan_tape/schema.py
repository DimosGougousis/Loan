"""Dutch mortgage loan-tape schema — Pydantic v2.

Single source of truth for the loan tape. Every analytics, validation, and
ECL path reads from this module. Field-by-field rationale documented in
``docs/domain-primer.md``. NL-tuned SICR triggers in ``docs/regulation-map.md``.

Schema discipline (from ``.claude/CLAUDE.md``):

- The schema is the contract. When adding a field: update schema → generator →
  validator → analytics, in that order.
- Cross-field invariants enforced here are *schema-level* (typing, IFRS 9 Stage 3
  backstop, HRA eligibility, PD monotonicity). The full validation engine in
  ``src/loan_tape/validate/rules.py`` enforces additional business rules
  with citations to BCBS 239 / NHG / Nibud / Tijdelijke regeling.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)


# ---------------------------------------------------------------------------
# Enums (NL-specific values)
# ---------------------------------------------------------------------------


class RateType(str, Enum):
    """Interest-rate type. NL banks distinguish *rentevast* (fixed) periods."""

    VARIABEL = "VARIABEL"
    RENTEVAST_5J = "RENTEVAST_5J"
    RENTEVAST_10J = "RENTEVAST_10J"
    RENTEVAST_20J = "RENTEVAST_20J"
    RENTEVAST_30J = "RENTEVAST_30J"


class RepaymentType(str, Enum):
    """NL-specific mortgage products.

    Only ANNUITEIT and LINEAIR originated since 2013 qualify for
    *hypotheekrenteaftrek* (HRA). The remaining types are legacy or specialty.
    """

    ANNUITEIT = "ANNUITEIT"
    LINEAIR = "LINEAIR"
    AFLOSSINGSVRIJ = "AFLOSSINGSVRIJ"
    BANKSPAAR = "BANKSPAAR"
    SPAAR = "SPAAR"
    BELEGGING = "BELEGGING"
    HYBRIDE = "HYBRIDE"


class PropertyType(str, Enum):
    """NL dwelling typology — drives liquidation discount in LGD."""

    APPARTEMENT = "APPARTEMENT"
    TUSSENWONING = "TUSSENWONING"
    HOEKWONING = "HOEKWONING"
    TWEE_ONDER_EEN_KAP = "2-ONDER-1-KAP"
    VRIJSTAAND = "VRIJSTAAND"


class BorrowerType(str, Enum):
    """Cohort distinction used by NHG and Nibud affordability rules."""

    STARTER = "STARTER"
    DOORSTROMER = "DOORSTROMER"
    OUDERE = "OUDERE"


class TaxatieType(str, Enum):
    """Valuation method. ECB AnaCredit attribute requires this distinction."""

    MARKETVALUE = "MARKETVALUE"
    EXECUTIEWAARDE = "EXECUTIEWAARDE"
    MODELMATIG = "MODELMATIG"


class EnergyLabel(str, Enum):
    """Dutch energy label — DNB climate-stress input."""

    A_PLUS_PLUS_PLUS_PLUS = "A++++"
    A_PLUS_PLUS_PLUS = "A+++"
    A_PLUS_PLUS = "A++"
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


class BkrScoreBand(str, Enum):
    """Bureau Krediet Registratie score band."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class IFRS9Stage(str, Enum):
    """IFRS 9 staging.

    Stage 1: performing (12-month ECL).
    Stage 2: SICR — significant increase in credit risk (lifetime ECL).
    Stage 3: credit-impaired (lifetime ECL).
    """

    ONE = "1"
    TWO = "2"
    THREE = "3"


class ArrearsBucket(str, Enum):
    """Days-past-due buckets used in roll-rate matrices."""

    ZERO = "0"
    BUCKET_1_30 = "1-30"
    BUCKET_31_60 = "31-60"
    BUCKET_61_90 = "61-90"
    NINETY_PLUS = "90+"


class SicrTrigger(str, Enum):
    """NL-tuned SICR triggers from §2.6.

    Sources:
    - QUANT_PD_INCREASE   — EBA GL/2017/06 + NL practice.
    - DPD_30_BACKSTOP     — IFRS 9 par. 5.5.11.
    - FORBEARANCE         — EBA forbearance definition.
    - WATCHLIST           — Internal credit policy.
    - MACRO_OVERLAY       — DNB 2024 sectoral guidance.
    - CLIMATE_TRANSITION  — DNB climate risk guidance.
    """

    NONE = "NONE"
    QUANT_PD_INCREASE = "QUANT_PD_INCREASE"
    DPD_30_BACKSTOP = "DPD_30_BACKSTOP"
    FORBEARANCE = "FORBEARANCE"
    WATCHLIST = "WATCHLIST"
    MACRO_OVERLAY = "MACRO_OVERLAY"
    CLIMATE_TRANSITION = "CLIMATE_TRANSITION"


# ---------------------------------------------------------------------------
# Annotated types — keep the model lean and the constraints explicit
# ---------------------------------------------------------------------------

Probability = Annotated[float, Field(ge=0.0, le=1.0)]
NonNegFloat = Annotated[float, Field(ge=0.0)]
NonNegInt = Annotated[int, Field(ge=0)]
EurAmount = Annotated[float, Field(ge=0.0)]
InterestRate = Annotated[float, Field(ge=0.0, lt=1.0)]
Bouwjaar = Annotated[int, Field(ge=1700, le=2100)]
PC6 = Annotated[str, Field(pattern=r"^\d{4}[A-Z]{2}$")]
HraPhaseOutRate = Annotated[float, Field(ge=0.0, le=0.55)]

HRA_TAX_REGIME_START = date(2013, 1, 1)
"""HRA eligibility cutoff. Loans originated before this date with annuity/linear
repayment are grandfathered into legacy treatment; for new originations the
post-2013 regime applies."""


# ---------------------------------------------------------------------------
# Placeholder (kept for the Day-0 smoke test until it is rewritten)
# ---------------------------------------------------------------------------


class LoanPlaceholder(BaseModel):
    """Lightweight placeholder used by the Day-0 smoke test.

    Will be removed once tests/unit/test_smoke.py is rewritten to use ``Loan``.
    """

    loan_id: str = Field(..., description="Primary key")
    ifrs9_stage: IFRS9Stage = Field(default=IFRS9Stage.ONE)


# ---------------------------------------------------------------------------
# The Dutch mortgage Loan model
# ---------------------------------------------------------------------------


class Loan(BaseModel):
    """A single Dutch residential-mortgage loan as it appears on a tape.

    The model enforces:

    1. Type + range constraints on every field.
    2. Enum membership for every categorical.
    3. Schema-level cross-field invariants — those that should be impossible to
       persist regardless of the analyst's workflow:
         - ``maturity_date > origination_date``
         - ``pd_lifetime >= pd_12m``
         - IFRS 9 Stage 3 backstop (dpd ≥ 90 OR UTP OR forborne)
         - HRA eligibility (post-2013 + annuity/linear)
    4. Derived (computed) fields: ``current_ltv``, ``original_lti``,
       ``expected_loss``.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        use_enum_values=False,
        str_strip_whitespace=True,
    )

    # ---- Borrower & contract --------------------------------------------
    loan_id: str = Field(..., min_length=1, description="Primary key (UUID-ish).")
    borrower_id: str = Field(..., min_length=1, description="FK; many loans → one borrower.")
    borrower_type: BorrowerType
    origination_date: date
    maturity_date: date
    original_principal: EurAmount
    current_balance: EurAmount
    interest_rate: InterestRate
    rate_type: RateType
    rentevast_einddatum: date | None = Field(
        default=None,
        description="When the rentevast period ends. Null for VARIABEL.",
    )
    repayment_type: RepaymentType
    tax_deduction_eligible: bool = Field(
        ...,
        description=(
            "True only for ANNUITEIT/LINEAIR originated on or after "
            "2013-01-01 (Dutch HRA regime)."
        ),
    )
    hra_phase_out_rate: HraPhaseOutRate
    interest_only_portion: EurAmount = Field(
        default=0.0,
        description="Portion of principal in interest-only form. EUR amount, not ratio.",
    )
    currency: str = Field(..., min_length=3, max_length=3)

    # ---- Collateral & property ------------------------------------------
    property_value_at_origination: EurAmount
    taxatie_waarde: EurAmount
    taxatie_date: date
    taxatie_type: TaxatieType
    woz_waarde: EurAmount
    woz_reference_date: date
    property_value_current: EurAmount
    pc6: PC6
    gemeente: str = Field(..., min_length=1)
    property_type: PropertyType
    bouwjaar: Bouwjaar
    energy_label: EnergyLabel
    nhg_flag: bool
    nhg_cap_at_origination: EurAmount
    nhg_premium_paid: EurAmount

    # ---- Credit-risk metrics (Basel + IFRS 9) ---------------------------
    pd_12m: Probability
    pd_lifetime: Probability
    lgd: Probability
    ead: EurAmount
    ifrs9_stage: IFRS9Stage
    sicr_trigger_reason: SicrTrigger = SicrTrigger.NONE
    days_past_due: NonNegInt
    arrears_bucket: ArrearsBucket
    restructured_flag: bool = False
    watchlist_flag: bool = False
    unlikely_to_pay_flag: bool = False
    risk_weight: Probability

    # ---- Borrower affordability (Nibud / Tijdelijke regeling) -----------
    gross_household_income: EurAmount
    partner_income_included: bool = False
    student_loan_debt: NonNegFloat = 0.0
    bkr_score_band: BkrScoreBand
    bkr_negative_registration_flag: bool = False
    dscr: NonNegFloat

    # -------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------

    @model_validator(mode="after")
    def _currency_is_eur_only(self) -> Loan:
        """This is a Dutch retail-mortgage tape — FX risk is nil."""
        if self.currency != "EUR":
            raise ValueError(
                f"currency must be 'EUR' for a Dutch mortgage tape, got {self.currency!r}"
            )
        return self

    @model_validator(mode="after")
    def _maturity_after_origination(self) -> Loan:
        if self.maturity_date <= self.origination_date:
            raise ValueError(
                f"maturity_date {self.maturity_date} must be after origination_date "
                f"{self.origination_date}"
            )
        return self

    @model_validator(mode="after")
    def _pd_lifetime_ge_pd_12m(self) -> Loan:
        """Lifetime PD must be ≥ 12-month PD by monotonicity of survival."""
        if self.pd_lifetime < self.pd_12m:
            raise ValueError(
                f"pd_lifetime ({self.pd_lifetime}) must be >= pd_12m ({self.pd_12m})"
            )
        return self

    @model_validator(mode="after")
    def _stage_3_backstop(self) -> Loan:
        """IFRS 9 par. 5.5.11 backstop — Stage 3 ⇒ (dpd≥90 OR UTP OR forborne).

        This is the *minimum* trigger set; the full SICR logic in
        ``src/loan_tape/ecl/sicr.py`` may layer additional criteria.
        """
        if self.ifrs9_stage == IFRS9Stage.THREE and not (
            self.days_past_due >= 90
            or self.unlikely_to_pay_flag
            or self.restructured_flag
        ):
            raise ValueError(
                "ifrs9_stage=3 requires days_past_due>=90 OR unlikely_to_pay_flag "
                "OR restructured_flag (IFRS 9 par. 5.5.11)"
            )
        return self

    @model_validator(mode="after")
    def _hra_eligibility(self) -> Loan:
        """*Hypotheekrenteaftrek* eligibility — post-2013, annuity or linear only."""
        if self.tax_deduction_eligible:
            if self.repayment_type not in (
                RepaymentType.ANNUITEIT,
                RepaymentType.LINEAIR,
            ):
                raise ValueError(
                    "tax_deduction_eligible=True requires repayment_type IN "
                    f"{{ANNUITEIT, LINEAIR}}, got {self.repayment_type.value}"
                )
            if self.origination_date < HRA_TAX_REGIME_START:
                raise ValueError(
                    "tax_deduction_eligible=True requires origination_date >= "
                    f"{HRA_TAX_REGIME_START} (Dutch HRA regime change)"
                )
        return self

    @model_validator(mode="after")
    def _pc6_format(self) -> Loan:
        """PC6 must be 4 digits + 2 uppercase letters (NL postal format).

        Redundant with the Annotated pattern, but keeps the error message
        domain-specific for the validation report.
        """
        if not re.fullmatch(r"\d{4}[A-Z]{2}", self.pc6):
            raise ValueError(
                f"pc6 {self.pc6!r} must match 4 digits + 2 uppercase letters "
                "(e.g. '1011AB')"
            )
        return self

    # -------------------------------------------------------------------
    # Derived (computed) fields
    # -------------------------------------------------------------------

    @computed_field  # type: ignore[prop-decorator]
    @property
    def current_ltv(self) -> float:
        """Current loan-to-value. Primary LGD driver in Dutch mortgages.

        Returns 0.0 if ``property_value_current`` is zero — caller's
        responsibility to interpret. The validation engine flags zero-valuation
        loans separately.
        """
        if self.property_value_current == 0:
            return 0.0
        return self.current_balance / self.property_value_current

    @computed_field  # type: ignore[prop-decorator]
    @property
    def original_lti(self) -> float:
        """Original loan-to-income. Regulated cap via *Tijdelijke regeling*."""
        if self.gross_household_income == 0:
            return 0.0
        return self.original_principal / self.gross_household_income

    @computed_field  # type: ignore[prop-decorator]
    @property
    def expected_loss(self) -> float:
        """IFRS 9 Expected Credit Loss.

        Stage 1: 12-month ECL = pd_12m × lgd × ead.
        Stage 2 / Stage 3: lifetime ECL = pd_lifetime × lgd × ead.
        """
        pd = self.pd_12m if self.ifrs9_stage == IFRS9Stage.ONE else self.pd_lifetime
        return pd * self.lgd * self.ead
