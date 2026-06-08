"""Integration eval — paired with ``evals/rubrics/validation_report.md``.

The runner in ``evals/runner.py`` discovers this file via the
``rubric.stem == test_<name>.py`` convention.

Eval criteria (from the rubric):

1. ≥ 95% of seeded issues on the easter-egg tape surface as findings.
2. 0 false-positive CRITICAL findings on the clean ``golden_tape.parquet``.
3. AnaCredit conformance ≥ 98% on the clean tape.
4. Every CRITICAL finding cites a regulation.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from loan_tape.generator import EasterEgg, generate_tape
from loan_tape.validate.anacredit import portfolio_conformance
from loan_tape.validate.rules import Severity, run_all_rules

pytestmark = pytest.mark.eval

REFERENCE_DATE = date(2025, 6, 1)
EASTER_EGG_SEED = 99
EASTER_EGG_N = 600
RECALL_TARGET = 0.95
CONFORMANCE_TARGET = 0.98


@pytest.fixture(scope="module")
def easter_egg_tape() -> pl.DataFrame:
    """A 600-loan tape with the 4 seeded easter eggs injected."""
    return generate_tape(n=EASTER_EGG_N, seed=EASTER_EGG_SEED, inject_easter_eggs=True)


def test_eval_no_false_positive_criticals_on_clean_tape(
    golden_tape: pl.DataFrame,
) -> None:
    """Rubric criterion 2: zero CRITICAL findings on the clean baseline."""
    results = run_all_rules(golden_tape, reference_date=REFERENCE_DATE)
    criticals = [r for r in results if r.severity == Severity.CRITICAL]
    assert criticals == [], (
        f"unexpected criticals on clean golden tape: "
        f"{[(c.rule_name, c.loan_id) for c in criticals[:5]]}"
    )


def test_eval_every_critical_cites_a_regulation(
    easter_egg_tape: pl.DataFrame,
) -> None:
    """Rubric criterion 4: every CRITICAL finding has a non-empty citation."""
    results = run_all_rules(easter_egg_tape, reference_date=REFERENCE_DATE)
    for r in results:
        if r.severity == Severity.CRITICAL:
            assert r.regulation, f"{r.rule_name} has empty regulation citation"


def test_eval_anacredit_conformance_on_clean_tape(
    golden_tape: pl.DataFrame,
) -> None:
    """Rubric criterion 3: ≥98% AnaCredit conformance on clean tape."""
    share, _ = portfolio_conformance(golden_tape)
    assert share >= CONFORMANCE_TARGET, (
        f"AnaCredit conformance {share:.4f} below target {CONFORMANCE_TARGET}"
    )


def test_eval_easter_egg_recall_meets_95pct(easter_egg_tape: pl.DataFrame) -> None:
    """Rubric criterion 1: ≥95% of seeded issues surface as findings.

    Two of the four easter eggs map cleanly to validation rules:
      - NHG_CAP_BREACH_BATCH        -> nhg_cap
      - HIGH_INTEREST_ONLY_CLUSTER  -> interest_only_cap
    The remaining two map to anomaly-detector territory (Day 2 PM #1):
      - HIGH_AFLOSSINGSVRIJ_COHORT  -> repayment-mix anomaly
      - STALE_TAXATIE_CLUSTER       -> taxatie_freshness when Stage 1
                                        (caught only when ifrs9_stage == 1)

    The validation engine claims recall on the two rule-mapped eggs and on
    Stage-1 stale-taxatie loans. ≥95% per egg is the rubric target.
    """
    results = run_all_rules(easter_egg_tape, reference_date=REFERENCE_DATE)
    failed_loan_ids_by_rule: dict[str, set[str]] = {}
    for r in results:
        failed_loan_ids_by_rule.setdefault(r.rule_name, set()).add(r.loan_id)

    # NHG cap egg → nhg_cap rule (every seeded row should surface)
    nhg_egg = easter_egg_tape.filter(
        pl.col("easter_egg") == EasterEgg.NHG_CAP_BREACH_BATCH.value
    )
    if nhg_egg.height:
        caught = sum(
            1
            for lid in nhg_egg["loan_id"]
            if lid in failed_loan_ids_by_rule.get("nhg_cap", set())
        )
        recall = caught / nhg_egg.height
        assert recall >= RECALL_TARGET, (
            f"nhg_cap recall on NHG_CAP_BREACH_BATCH = {recall:.2f} "
            f"< {RECALL_TARGET}"
        )

    # Interest-only egg → interest_only_cap rule
    io_egg = easter_egg_tape.filter(
        pl.col("easter_egg") == EasterEgg.HIGH_INTEREST_ONLY_CLUSTER.value
    )
    if io_egg.height:
        caught = sum(
            1
            for lid in io_egg["loan_id"]
            if lid in failed_loan_ids_by_rule.get("interest_only_cap", set())
        )
        recall = caught / io_egg.height
        assert recall >= RECALL_TARGET, (
            f"interest_only_cap recall on HIGH_INTEREST_ONLY_CLUSTER = "
            f"{recall:.2f} < {RECALL_TARGET}"
        )

    # Stale taxatie egg → taxatie_freshness rule, but only for Stage 1 loans
    stale_egg_s1 = easter_egg_tape.filter(
        (pl.col("easter_egg") == EasterEgg.STALE_TAXATIE_CLUSTER.value)
        & (pl.col("ifrs9_stage") == "1")
    )
    if stale_egg_s1.height:
        caught = sum(
            1
            for lid in stale_egg_s1["loan_id"]
            if lid in failed_loan_ids_by_rule.get("taxatie_freshness", set())
        )
        recall = caught / stale_egg_s1.height
        assert recall >= RECALL_TARGET, (
            f"taxatie_freshness recall on STALE_TAXATIE_CLUSTER (Stage 1) = "
            f"{recall:.2f} < {RECALL_TARGET}"
        )
