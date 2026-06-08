"""Quick Scan analytics tests — pure-function KPI calculations (RED first)."""

from __future__ import annotations

import polars as pl
import pytest

from loan_tape.analytics.quick_scan import (
    QuickScanKPIs,
    compute_quick_scan,
    vintage_histogram,
)


def test_quick_scan_kpis_match_golden_tape(golden_tape: pl.DataFrame) -> None:
    kpis = compute_quick_scan(golden_tape)
    assert isinstance(kpis, QuickScanKPIs)
    assert kpis.loan_count == golden_tape.shape[0]
    assert kpis.borrower_count <= kpis.loan_count
    assert kpis.total_exposure == pytest.approx(
        golden_tape["current_balance"].sum(), rel=1e-9
    )


def test_quick_scan_weighted_avg_pd_in_unit_range(golden_tape: pl.DataFrame) -> None:
    kpis = compute_quick_scan(golden_tape)
    assert 0.0 <= kpis.weighted_avg_pd_12m <= 1.0
    assert 0.0 <= kpis.weighted_avg_pd_lifetime <= 1.0


def test_quick_scan_weighted_avg_ltv_positive(golden_tape: pl.DataFrame) -> None:
    kpis = compute_quick_scan(golden_tape)
    assert kpis.weighted_avg_current_ltv > 0.0
    assert kpis.weighted_avg_current_ltv < 1.5  # reasonable upper bound


def test_quick_scan_stage_mix_sums_to_one(golden_tape: pl.DataFrame) -> None:
    kpis = compute_quick_scan(golden_tape)
    assert "1" in kpis.ifrs9_stage_mix
    assert "2" in kpis.ifrs9_stage_mix
    assert "3" in kpis.ifrs9_stage_mix
    total = sum(kpis.ifrs9_stage_mix.values())
    assert total == pytest.approx(1.0, abs=1e-6)


def test_quick_scan_nhg_share_in_unit_range(golden_tape: pl.DataFrame) -> None:
    kpis = compute_quick_scan(golden_tape)
    assert 0.0 <= kpis.nhg_share <= 1.0


def test_quick_scan_energy_label_mix_sums_to_one(golden_tape: pl.DataFrame) -> None:
    kpis = compute_quick_scan(golden_tape)
    assert sum(kpis.energy_label_mix.values()) == pytest.approx(1.0, abs=1e-6)


def test_quick_scan_aflossingsvrij_share(golden_tape: pl.DataFrame) -> None:
    kpis = compute_quick_scan(golden_tape)
    direct = (
        golden_tape.filter(pl.col("repayment_type") == "AFLOSSINGSVRIJ").height
        / golden_tape.height
    )
    assert kpis.aflossingsvrij_share == pytest.approx(direct)


def test_quick_scan_weighted_avg_hra_in_legal_range(golden_tape: pl.DataFrame) -> None:
    kpis = compute_quick_scan(golden_tape)
    # HRA max rate is 0..0.55 per the validation rule
    assert 0.0 <= kpis.weighted_avg_hra_phase_out_rate <= 0.55


def test_quick_scan_on_empty_tape_returns_safe_zeros() -> None:
    """Fail-gracefully: empty cohort renders without crashing."""
    empty = pl.DataFrame(
        schema={
            "loan_id": pl.Utf8,
            "borrower_id": pl.Utf8,
            "current_balance": pl.Float64,
            "pd_12m": pl.Float64,
            "pd_lifetime": pl.Float64,
            "current_ltv": pl.Float64,
            "ead": pl.Float64,
            "ifrs9_stage": pl.Utf8,
            "nhg_flag": pl.Boolean,
            "energy_label": pl.Utf8,
            "repayment_type": pl.Utf8,
            "hra_phase_out_rate": pl.Float64,
            "origination_date": pl.Date,
        }
    )
    kpis = compute_quick_scan(empty)
    assert kpis.loan_count == 0
    assert kpis.total_exposure == 0.0


def test_vintage_histogram_returns_year_counts(golden_tape: pl.DataFrame) -> None:
    hist = vintage_histogram(golden_tape)
    assert "year" in hist.columns
    assert "loan_count" in hist.columns
    assert hist["loan_count"].sum() == golden_tape.shape[0]
