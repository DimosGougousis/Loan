"""Quick Scan analytics — portfolio KPIs computed as pure functions.

Used by ``app/pages/1_Quick_Scan.py``. Every metric is a function of the
input ``pl.DataFrame`` so the same logic runs in CLI, Streamlit, and tests.

Fail-gracefully §7.7.1 stage 3: empty cohort returns ``QuickScanKPIs`` with
zeros, not NaN/Inf. The page is responsible for rendering "no data" panels
when ``loan_count == 0``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

# Re-used by the schema, validation, and ECL paths.
_STAGES: tuple[str, ...] = ("1", "2", "3")


@dataclass(frozen=True)
class QuickScanKPIs:
    """Portfolio-level KPIs surfaced by the Quick Scan page."""

    loan_count: int
    borrower_count: int
    total_exposure: float
    weighted_avg_pd_12m: float
    weighted_avg_pd_lifetime: float
    weighted_avg_current_ltv: float
    weighted_avg_hra_phase_out_rate: float
    nhg_share: float
    aflossingsvrij_share: float
    ifrs9_stage_mix: dict[str, float] = field(default_factory=dict)
    energy_label_mix: dict[str, float] = field(default_factory=dict)


def _safe_weighted_mean(values: pl.Series, weights: pl.Series) -> float:
    total = weights.sum()
    if total == 0:
        return 0.0
    return float((values * weights).sum() / total)


def compute_quick_scan(tape: pl.DataFrame) -> QuickScanKPIs:
    """Compute every Quick Scan KPI from a loan tape.

    Pure function. Handles the empty tape per the fail-gracefully playbook.
    """
    n = tape.shape[0]
    if n == 0:
        return QuickScanKPIs(
            loan_count=0,
            borrower_count=0,
            total_exposure=0.0,
            weighted_avg_pd_12m=0.0,
            weighted_avg_pd_lifetime=0.0,
            weighted_avg_current_ltv=0.0,
            weighted_avg_hra_phase_out_rate=0.0,
            nhg_share=0.0,
            aflossingsvrij_share=0.0,
            ifrs9_stage_mix={s: 0.0 for s in _STAGES},
            energy_label_mix={},
        )

    weights = tape["current_balance"]
    pd_12m = _safe_weighted_mean(tape["pd_12m"], weights)
    pd_lifetime = _safe_weighted_mean(tape["pd_lifetime"], weights)

    # current_ltv may be missing on persisted tapes (it's computed on-the-fly
    # in the schema); derive if absent.
    if "current_ltv" in tape.columns:
        ltv_series = tape["current_ltv"]
    else:
        ltv_series = (
            tape["current_balance"] / tape["property_value_current"].replace(0, 1.0)
        )
    weighted_ltv = _safe_weighted_mean(ltv_series, weights)
    weighted_hra = _safe_weighted_mean(tape["hra_phase_out_rate"], weights)

    nhg_share = float(tape["nhg_flag"].sum()) / n
    aflossingsvrij_share = (
        float(tape.filter(pl.col("repayment_type") == "AFLOSSINGSVRIJ").height) / n
    )

    stage_mix: dict[str, float] = {s: 0.0 for s in _STAGES}
    stage_counts = (
        tape.group_by("ifrs9_stage").len().sort("ifrs9_stage")
    )
    for row in stage_counts.iter_rows(named=True):
        stage_mix[str(row["ifrs9_stage"])] = float(row["len"]) / n

    energy_mix: dict[str, float] = {}
    energy_counts = tape.group_by("energy_label").len()
    for row in energy_counts.iter_rows(named=True):
        energy_mix[str(row["energy_label"])] = float(row["len"]) / n

    return QuickScanKPIs(
        loan_count=n,
        borrower_count=tape["borrower_id"].n_unique(),
        total_exposure=float(weights.sum()),
        weighted_avg_pd_12m=pd_12m,
        weighted_avg_pd_lifetime=pd_lifetime,
        weighted_avg_current_ltv=weighted_ltv,
        weighted_avg_hra_phase_out_rate=weighted_hra,
        nhg_share=nhg_share,
        aflossingsvrij_share=aflossingsvrij_share,
        ifrs9_stage_mix=stage_mix,
        energy_label_mix=energy_mix,
    )


def vintage_histogram(tape: pl.DataFrame) -> pl.DataFrame:
    """Origination-year loan counts. Returns columns: ``year``, ``loan_count``."""
    if tape.shape[0] == 0:
        return pl.DataFrame({"year": [], "loan_count": []})
    return (
        tape.with_columns(year=pl.col("origination_date").dt.year())
        .group_by("year")
        .len()
        .rename({"len": "loan_count"})
        .sort("year")
    )
