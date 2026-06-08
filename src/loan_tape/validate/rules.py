"""Validation engine — 9 NL-specific cross-field rules.

Spec: plan §5.5. Each rule cites a regulation in the ``regulation`` field of
its ``RuleResult`` and a BCBS 239 data-quality dimension. Adding a rule
requires updates documented in ``.claude/skills/add-validation-rule.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Callable

import polars as pl

from loan_tape.schema import Loan, RepaymentType

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Severity bands for validation findings.

    CRITICAL — regulatory breach; blocks Publish per §7.7.1 stage 2.
    HIGH     — data quality issue affecting EL calculation.
    MEDIUM   — freshness / completeness gap.
    LOW      — cosmetic or advisory.
    """

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Bcbs239Dimension(str, Enum):
    """BCBS 239 data-quality dimensions."""

    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    TIMELINESS = "timeliness"
    INTEGRITY = "integrity"


@dataclass(frozen=True)
class RuleResult:
    """Outcome of running one rule against one loan."""

    passed: bool
    severity: Severity
    loan_id: str
    rule_name: str
    regulation: str
    bcbs239_dimension: str
    message: str

    @classmethod
    def passed_for(
        cls,
        loan: Loan,
        rule_name: str,
        regulation: str,
        bcbs239_dimension: Bcbs239Dimension,
    ) -> RuleResult:
        return cls(
            passed=True,
            severity=Severity.LOW,
            loan_id=loan.loan_id,
            rule_name=rule_name,
            regulation=regulation,
            bcbs239_dimension=bcbs239_dimension.value,
            message="OK",
        )


RuleFn = Callable[[Loan], RuleResult]


# ---------------------------------------------------------------------------
# Rule 1 — Negative amortization
# ---------------------------------------------------------------------------


def negative_amortization_rule(loan: Loan) -> RuleResult:
    """current_balance must not exceed original_principal × 1.001.

    Source: schema-level integrity check. Catches data-entry mistakes that
    would otherwise produce nonsensical EL or LTV.
    """
    name = "negative_amortization"
    reg = "Schema integrity (internal)"
    dim = Bcbs239Dimension.INTEGRITY
    tolerance = 1.001
    if loan.current_balance > loan.original_principal * tolerance:
        return RuleResult(
            passed=False,
            severity=Severity.CRITICAL,
            loan_id=loan.loan_id,
            rule_name=name,
            regulation=reg,
            bcbs239_dimension=dim.value,
            message=(
                f"current_balance {loan.current_balance:,.0f} exceeds "
                f"original_principal {loan.original_principal:,.0f} (tolerance 0.1%)"
            ),
        )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Rule 2 — IFRS 9 Stage 3 backstop (already enforced at schema, re-checked here
# for explicit reporting + audit trail)
# ---------------------------------------------------------------------------


def stage_3_backstop_rule(loan: Loan) -> RuleResult:
    name = "stage_3_backstop"
    reg = "IFRS 9 par. 5.5.11"
    dim = Bcbs239Dimension.INTEGRITY
    if loan.ifrs9_stage.value == "3":
        if not (
            loan.days_past_due >= 90
            or loan.unlikely_to_pay_flag
            or loan.restructured_flag
        ):
            return RuleResult(
                passed=False,
                severity=Severity.CRITICAL,
                loan_id=loan.loan_id,
                rule_name=name,
                regulation=reg,
                bcbs239_dimension=dim.value,
                message=(
                    "Stage 3 loan with dpd<90 and no UTP/forborne flag "
                    "violates IFRS 9 backstop"
                ),
            )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Rule 3 — NHG cap
# ---------------------------------------------------------------------------


def nhg_cap_rule(loan: Loan) -> RuleResult:
    """nhg_flag ⇒ original_principal ≤ year-of-origination NHG cap.

    Source: NHG / WEW annual cap publication.
    """
    name = "nhg_cap"
    reg = "NHG / WEW annual cap"
    dim = Bcbs239Dimension.INTEGRITY
    if loan.nhg_flag and loan.original_principal > loan.nhg_cap_at_origination:
        return RuleResult(
            passed=False,
            severity=Severity.CRITICAL,
            loan_id=loan.loan_id,
            rule_name=name,
            regulation=reg,
            bcbs239_dimension=dim.value,
            message=(
                f"NHG-flagged loan exceeds NHG cap: "
                f"{loan.original_principal:,.0f} > "
                f"{loan.nhg_cap_at_origination:,.0f}"
            ),
        )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Rule 4 — HRA eligibility (schema-enforced; explicit echo)
# ---------------------------------------------------------------------------


HRA_REGIME_START = date(2013, 1, 1)


def hra_eligibility_rule(loan: Loan) -> RuleResult:
    name = "hra_eligibility"
    reg = "Hypotheekrenteaftrek regime (Belastingdienst), post-2013"
    dim = Bcbs239Dimension.INTEGRITY
    if loan.tax_deduction_eligible:
        ok_type = loan.repayment_type in (
            RepaymentType.ANNUITEIT,
            RepaymentType.LINEAIR,
        )
        ok_date = loan.origination_date >= HRA_REGIME_START
        if not (ok_type and ok_date):
            return RuleResult(
                passed=False,
                severity=Severity.HIGH,
                loan_id=loan.loan_id,
                rule_name=name,
                regulation=reg,
                bcbs239_dimension=dim.value,
                message=(
                    "tax_deduction_eligible=True with non-eligible "
                    f"repayment_type {loan.repayment_type.value} or "
                    f"pre-2013 origination_date {loan.origination_date}"
                ),
            )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Rule 5 — LTV consistency
# ---------------------------------------------------------------------------


LTV_TOLERANCE = 0.005  # 50 bps


def ltv_consistency_rule(loan: Loan) -> RuleResult:
    """Schema computes current_ltv; this rule re-checks against stored values."""
    name = "ltv_consistency"
    reg = "BCBS 239 (data accuracy)"
    dim = Bcbs239Dimension.ACCURACY
    if loan.property_value_current == 0:
        return RuleResult(
            passed=False,
            severity=Severity.HIGH,
            loan_id=loan.loan_id,
            rule_name=name,
            regulation=reg,
            bcbs239_dimension=dim.value,
            message="property_value_current is 0 — LTV undefined",
        )
    expected = loan.current_balance / loan.property_value_current
    if abs(expected - loan.current_ltv) > LTV_TOLERANCE:
        return RuleResult(
            passed=False,
            severity=Severity.HIGH,
            loan_id=loan.loan_id,
            rule_name=name,
            regulation=reg,
            bcbs239_dimension=dim.value,
            message=(
                f"current_ltv {loan.current_ltv:.4f} differs from "
                f"derived {expected:.4f} by > {LTV_TOLERANCE}"
            ),
        )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Rule 6 — PD monotonicity (schema-enforced; explicit echo)
# ---------------------------------------------------------------------------


def pd_monotonicity_rule(loan: Loan) -> RuleResult:
    name = "pd_monotonicity"
    reg = "Survival-analysis monotonicity"
    dim = Bcbs239Dimension.INTEGRITY
    if loan.pd_lifetime < loan.pd_12m:
        return RuleResult(
            passed=False,
            severity=Severity.HIGH,
            loan_id=loan.loan_id,
            rule_name=name,
            regulation=reg,
            bcbs239_dimension=dim.value,
            message=(
                f"pd_lifetime {loan.pd_lifetime} < pd_12m {loan.pd_12m}"
            ),
        )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Rule 7 — Stage 1 taxatie freshness
# ---------------------------------------------------------------------------


FRESH_MAX_MONTHS_STAGE_1 = 36


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def taxatie_freshness_rule(
    loan: Loan, reference_date: date | None = None
) -> RuleResult:
    """Stage 1 loans should have taxatie ≤ 36 months old.

    Source: BCBS 239 timeliness + Dutch CRR III prudential expectations on
    collateral valuation updates.
    """
    name = "taxatie_freshness"
    reg = "BCBS 239 (timeliness) + CRR III collateral valuation"
    dim = Bcbs239Dimension.TIMELINESS
    if loan.ifrs9_stage.value != "1":
        return RuleResult.passed_for(loan, name, reg, dim)
    ref = reference_date or date.today()
    age_months = _months_between(loan.taxatie_date, ref)
    if age_months > FRESH_MAX_MONTHS_STAGE_1:
        return RuleResult(
            passed=False,
            severity=Severity.MEDIUM,
            loan_id=loan.loan_id,
            rule_name=name,
            regulation=reg,
            bcbs239_dimension=dim.value,
            message=(
                f"Stage 1 loan with taxatie_date {loan.taxatie_date} is "
                f"{age_months} months old (> {FRESH_MAX_MONTHS_STAGE_1})"
            ),
        )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Rule 8 — LTI cap (Tijdelijke regeling / Nibud)
# ---------------------------------------------------------------------------


# Conservative blanket cap, irrespective of income band. Below the highest
# Nibud LTI factor for the year. Tighter income-banded caps live in
# data/reference/nibud_lti.csv and are checked by a future income-banded rule.
LTI_HARD_CAP = 6.0


def lti_cap_rule(loan: Loan) -> RuleResult:
    name = "lti_cap"
    reg = "Tijdelijke regeling hypothecair krediet (Min. Fin. + AFM) + Nibud"
    dim = Bcbs239Dimension.INTEGRITY
    if loan.original_lti > LTI_HARD_CAP:
        return RuleResult(
            passed=False,
            severity=Severity.HIGH,
            loan_id=loan.loan_id,
            rule_name=name,
            regulation=reg,
            bcbs239_dimension=dim.value,
            message=(
                f"original_lti {loan.original_lti:.2f} exceeds hard cap "
                f"{LTI_HARD_CAP} (income-banded Nibud cap stricter)"
            ),
        )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Rule 9 — Interest-only cap on HRA-eligible loans
# ---------------------------------------------------------------------------


INTEREST_ONLY_CAP_RATIO = 0.5


def interest_only_cap_rule(loan: Loan) -> RuleResult:
    """For HRA-eligible loans, interest_only_portion ≤ 50% of property value."""
    name = "interest_only_cap"
    reg = "Hypotheekrenteaftrek regime (Belastingdienst) interest-only cap"
    dim = Bcbs239Dimension.INTEGRITY
    if not loan.tax_deduction_eligible:
        return RuleResult.passed_for(loan, name, reg, dim)
    max_io = loan.property_value_at_origination * INTEREST_ONLY_CAP_RATIO
    if loan.interest_only_portion > max_io:
        return RuleResult(
            passed=False,
            severity=Severity.HIGH,
            loan_id=loan.loan_id,
            rule_name=name,
            regulation=reg,
            bcbs239_dimension=dim.value,
            message=(
                f"interest_only_portion {loan.interest_only_portion:,.0f} "
                f"exceeds 50% of property value {max_io:,.0f} on HRA-eligible loan"
            ),
        )
    return RuleResult.passed_for(loan, name, reg, dim)


# ---------------------------------------------------------------------------
# Registry + portfolio runner
# ---------------------------------------------------------------------------

RULE_REGISTRY: dict[str, RuleFn] = {
    "negative_amortization": negative_amortization_rule,
    "stage_3_backstop": stage_3_backstop_rule,
    "nhg_cap": nhg_cap_rule,
    "hra_eligibility": hra_eligibility_rule,
    "ltv_consistency": ltv_consistency_rule,
    "pd_monotonicity": pd_monotonicity_rule,
    "taxatie_freshness": taxatie_freshness_rule,
    "lti_cap": lti_cap_rule,
    "interest_only_cap": interest_only_cap_rule,
}


def run_all_rules(
    tape: pl.DataFrame,
    reference_date: date | None = None,
) -> list[RuleResult]:
    """Run every registered rule against every loan in ``tape``.

    Returns only *failed* results, plus a per-rule summary row marker is left
    to the caller (see ``validate.report.render_html``).
    """
    payload_cols = [c for c in tape.columns if c != "easter_egg"]
    failures: list[RuleResult] = []
    for row in tape.select(payload_cols).to_dicts():
        try:
            loan = Loan(**row)
        except Exception:  # noqa: BLE001 — schema violations surfaced by loaders
            continue
        for name, fn in RULE_REGISTRY.items():
            if name == "taxatie_freshness":
                result = taxatie_freshness_rule(loan, reference_date=reference_date)
            else:
                result = fn(loan)
            if not result.passed:
                failures.append(result)
    return failures
