"""Dutch synthetic mortgage tape generator.

Pure function: ``(n, seed) -> polars.DataFrame``. Every row satisfies the
``Loan`` Pydantic schema. Encodes NL realism documented in
``docs/domain-primer.md`` and the four named easter eggs from plan §2.5.

Usage (CLI)::

    uv run python -m loan_tape.generator --seed 42 --n 10000 \\
        --out data/samples/synthetic_tape_v1.parquet

Usage (library)::

    from loan_tape.generator import generate_tape
    tape = generate_tape(n=10_000, seed=42)
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from enum import Enum
from pathlib import Path

import numpy as np
import polars as pl

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
# Easter eggs (seeded anomaly cohorts) — plan §2.5
# ---------------------------------------------------------------------------


class EasterEgg(str, Enum):
    """Named anomaly cohorts injected for validation/anomaly testing."""

    HIGH_AFLOSSINGSVRIJ_COHORT = "HIGH_AFLOSSINGSVRIJ_COHORT"
    STALE_TAXATIE_CLUSTER = "STALE_TAXATIE_CLUSTER"
    NHG_CAP_BREACH_BATCH = "NHG_CAP_BREACH_BATCH"
    HIGH_INTEREST_ONLY_CLUSTER = "HIGH_INTEREST_ONLY_CLUSTER"


EASTER_EGG_KEYS: tuple[EasterEgg, ...] = tuple(EasterEgg)


# ---------------------------------------------------------------------------
# NL reference data — loaded from data/reference/ (real public values)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REFERENCE_DIR = REPO_ROOT / "data" / "reference"


def _load_nhg_caps() -> dict[int, float]:
    caps: dict[int, float] = {}
    with (REFERENCE_DIR / "nhg_caps.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            caps[int(row["year"])] = float(row["nhg_cap_eur"])
    return caps


def _load_hra_rates() -> dict[int, float]:
    rates: dict[int, float] = {}
    with (REFERENCE_DIR / "hra_rates.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rates[int(row["year"])] = float(row["max_hra_rate_pct"]) / 100.0
    return rates


NHG_CAPS: dict[int, float] = _load_nhg_caps()
HRA_RATES: dict[int, float] = _load_hra_rates()


def _hra_rate_for(year: int) -> float:
    """Lookup HRA max rate for a year, clamping to the table range."""
    if year in HRA_RATES:
        return HRA_RATES[year]
    if year < min(HRA_RATES):
        return HRA_RATES[min(HRA_RATES)]
    return HRA_RATES[max(HRA_RATES)]


def _nhg_cap_for(year: int) -> float:
    """Lookup NHG cap for an origination year, clamping to table range."""
    if year in NHG_CAPS:
        return NHG_CAPS[year]
    if year < min(NHG_CAPS):
        return NHG_CAPS[min(NHG_CAPS)]
    return NHG_CAPS[max(NHG_CAPS)]


# ---------------------------------------------------------------------------
# Geography seeds — representative subset; full mapping lives in
# data/reference/pc6_to_gemeente.parquet (loaded by analytics, not the generator)
# ---------------------------------------------------------------------------

# (pc4_prefix, gemeente, price_uplift_factor, randstad_flag)
_GEO_ANCHORS: tuple[tuple[str, str, float, bool], ...] = (
    ("1011", "Amsterdam", 1.75, True),
    ("1071", "Amsterdam", 1.85, True),
    ("2511", "Den Haag", 1.45, True),
    ("3011", "Rotterdam", 1.30, True),
    ("3511", "Utrecht", 1.55, True),
    ("5611", "Eindhoven", 1.10, False),
    ("9711", "Groningen", 0.90, False),
    ("8911", "Leeuwarden", 0.80, False),
    ("6211", "Maastricht", 0.95, False),
    ("7511", "Enschede", 0.85, False),
    ("4811", "Breda", 1.05, False),
    ("2011", "Haarlem", 1.40, True),
)


def _pc6_from_anchor(anchor_idx: int, rng: np.random.Generator) -> str:
    """Build a valid PC6 (4 digits + 2 uppercase letters) from an anchor PC4."""
    prefix = _GEO_ANCHORS[anchor_idx][0]
    letters = "".join(
        chr(ord("A") + i) for i in rng.integers(0, 26, size=2, endpoint=False)
    )
    return f"{prefix}{letters}"


# ---------------------------------------------------------------------------
# Distribution helpers
# ---------------------------------------------------------------------------


def _repayment_type_for_vintage(year: int, rng: np.random.Generator) -> RepaymentType:
    """NL repayment-type mix — vintage-correlated.

    Pre-2013: mixed, with notable AFLOSSINGSVRIJ/SPAAR/HYBRIDE legacy share.
    Post-2013: dominantly ANNUITEIT (HRA-driven), some LINEAR, small AFLOSSINGSVRIJ.
    """
    if year < 2013:
        probs = {
            RepaymentType.ANNUITEIT: 0.30,
            RepaymentType.LINEAIR: 0.10,
            RepaymentType.AFLOSSINGSVRIJ: 0.30,
            RepaymentType.SPAAR: 0.15,
            RepaymentType.BANKSPAAR: 0.05,
            RepaymentType.HYBRIDE: 0.07,
            RepaymentType.BELEGGING: 0.03,
        }
    else:
        probs = {
            RepaymentType.ANNUITEIT: 0.72,
            RepaymentType.LINEAIR: 0.18,
            RepaymentType.AFLOSSINGSVRIJ: 0.06,
            RepaymentType.SPAAR: 0.0,
            RepaymentType.BANKSPAAR: 0.01,
            RepaymentType.HYBRIDE: 0.02,
            RepaymentType.BELEGGING: 0.01,
        }
    types = list(probs.keys())
    p = np.array(list(probs.values()))
    p = p / p.sum()
    return types[int(rng.choice(len(types), p=p))]


def _energy_label_for_bouwjaar(year: int, rng: np.random.Generator) -> EnergyLabel:
    """Energy label by construction year. Pre-1992 skews C-G; post-2015 A/A+."""
    if year < 1992:
        labels = (
            EnergyLabel.C,
            EnergyLabel.D,
            EnergyLabel.E,
            EnergyLabel.F,
            EnergyLabel.G,
        )
        probs = np.array([0.18, 0.22, 0.22, 0.20, 0.18])
    elif year < 2015:
        labels = (
            EnergyLabel.A,
            EnergyLabel.B,
            EnergyLabel.C,
            EnergyLabel.D,
            EnergyLabel.E,
        )
        probs = np.array([0.15, 0.30, 0.30, 0.15, 0.10])
    else:
        labels = (
            EnergyLabel.A_PLUS_PLUS_PLUS_PLUS,
            EnergyLabel.A_PLUS_PLUS_PLUS,
            EnergyLabel.A_PLUS_PLUS,
            EnergyLabel.A_PLUS,
            EnergyLabel.A,
            EnergyLabel.B,
        )
        probs = np.array([0.05, 0.15, 0.25, 0.30, 0.20, 0.05])
    return labels[int(rng.choice(len(labels), p=probs / probs.sum()))]


def _rate_type_for_vintage(year: int, rng: np.random.Generator) -> RateType:
    """Rate-type mix tuned to surface the 2025-2028 *rentevast* reset cohort.

    The 2015-2020 vintage skews toward 5/10-year fixes so their end-dates land
    in 2020-2030 (heavy in 2025-2028). 2010-2014 vintage takes some 10/20-year
    fixes whose end-dates land 2020-2034. Recent vintages (>2020) favor
    longer fixes (interest-rate hedge).
    """
    types = (
        RateType.VARIABEL,
        RateType.RENTEVAST_5J,
        RateType.RENTEVAST_10J,
        RateType.RENTEVAST_20J,
        RateType.RENTEVAST_30J,
    )
    if year < 2015:
        # Pre-2015 + 10J/20J endings land 2025-2035 — feeds reset cohort tail.
        probs = np.array([0.10, 0.15, 0.40, 0.25, 0.10])
    elif year < 2021:
        # 2015-2020: 5J + 10J ≈ 80% — engine of the 2025-2028 reset wave.
        probs = np.array([0.05, 0.35, 0.45, 0.10, 0.05])
    else:
        # 2021-2025 + 5J endings land 2026-2030 — partly inside the window.
        probs = np.array([0.05, 0.20, 0.40, 0.25, 0.10])
    return types[int(rng.choice(len(types), p=probs / probs.sum()))]


def _rentevast_einddatum(
    origination: date, rate_type: RateType, rng: np.random.Generator
) -> date | None:
    """End date of the rentevast period — drives the 2025-2028 reset cohort."""
    if rate_type == RateType.VARIABEL:
        return None
    years_map = {
        RateType.RENTEVAST_5J: 5,
        RateType.RENTEVAST_10J: 10,
        RateType.RENTEVAST_20J: 20,
        RateType.RENTEVAST_30J: 30,
    }
    years = years_map[rate_type]
    return origination + timedelta(days=365 * years + int(rng.integers(-30, 31)))


# ---------------------------------------------------------------------------
# Single-row generator (used inside the vectorized loop)
# ---------------------------------------------------------------------------


def _generate_row(  # noqa: PLR0915
    rng: np.random.Generator, idx: int, id_prefix: str = "0000"
) -> dict[str, object]:
    """Generate one schema-conformant loan row.

    Order of field generation matches the schema document layout so dependencies
    are linear (e.g., property_value_current depends on taxatie_waarde).
    """
    # Vintage: tilt toward more recent years
    vintage_years = np.arange(2010, 2026)
    vintage_weights = np.linspace(0.5, 1.8, len(vintage_years))
    vintage_weights = vintage_weights / vintage_weights.sum()
    orig_year = int(rng.choice(vintage_years, p=vintage_weights))
    orig_month = int(rng.integers(1, 13))
    orig_day = int(rng.integers(1, 29))
    origination = date(orig_year, orig_month, orig_day)

    repayment_type = _repayment_type_for_vintage(orig_year, rng)
    rate_type = _rate_type_for_vintage(orig_year, rng)
    rentevast_einddatum = _rentevast_einddatum(origination, rate_type, rng)

    term_years = int(rng.choice([20, 25, 30, 30, 30]))  # 30-year dominant
    maturity = origination + timedelta(days=365 * term_years)

    # Geography
    anchor_idx = int(rng.integers(0, len(_GEO_ANCHORS)))
    _, gemeente, uplift, _randstad = _GEO_ANCHORS[anchor_idx]
    pc6 = _pc6_from_anchor(anchor_idx, rng)

    # Property
    bouwjaar = int(rng.integers(1900, 2024))
    property_type_pool = list(PropertyType)
    property_type = property_type_pool[int(rng.integers(0, len(property_type_pool)))]
    energy_label = _energy_label_for_bouwjaar(bouwjaar, rng)

    base_value = float(rng.normal(280_000, 60_000))
    base_value = max(110_000.0, base_value)
    property_value_at_origination = round(base_value * uplift, 2)
    taxatie_waarde = property_value_at_origination
    # WOZ typically lags ~10-20%
    woz_waarde = round(taxatie_waarde * float(rng.uniform(0.80, 0.95)), 2)
    woz_reference_date = date(min(orig_year + 1, 2025), 1, 1)
    taxatie_date = origination - timedelta(days=int(rng.integers(0, 60)))
    taxatie_type = TaxatieType.MARKETVALUE

    # House-price index uplift to current
    years_since = 2025 - orig_year
    hpi_uplift = float(np.prod(1 + rng.normal(0.04, 0.03, size=max(years_since, 0))))
    property_value_current = round(taxatie_waarde * max(hpi_uplift, 0.7), 2)

    # Loan size
    ltv_target = float(rng.uniform(0.55, 0.95))
    original_principal = round(property_value_at_origination * ltv_target, 2)

    # Amortization (simple proxy by years elapsed)
    elapsed_frac = min(years_since / term_years, 0.95)
    amort_frac = (
        0.0
        if repayment_type == RepaymentType.AFLOSSINGSVRIJ
        else elapsed_frac * float(rng.uniform(0.6, 1.0))
    )
    current_balance = round(original_principal * (1 - amort_frac), 2)

    # Interest-only portion (EUR amount)
    if repayment_type == RepaymentType.AFLOSSINGSVRIJ:
        interest_only_portion = round(original_principal * float(rng.uniform(0.8, 1.0)), 2)
    elif repayment_type == RepaymentType.HYBRIDE:
        interest_only_portion = round(original_principal * float(rng.uniform(0.3, 0.5)), 2)
    else:
        interest_only_portion = 0.0

    # NHG
    nhg_cap = _nhg_cap_for(orig_year)
    nhg_eligible = original_principal <= nhg_cap
    nhg_flag = bool(nhg_eligible and rng.random() < 0.55)
    nhg_premium = round(original_principal * 0.005, 2) if nhg_flag else 0.0

    # HRA eligibility (post-2013 + ANNUITEIT/LINEAIR)
    tax_deduction_eligible = bool(
        origination >= date(2013, 1, 1)
        and repayment_type in (RepaymentType.ANNUITEIT, RepaymentType.LINEAIR)
    )
    hra_phase_out_rate = _hra_rate_for(orig_year)

    # Interest rate (vintage-dependent)
    rate_by_year = {
        2010: 0.045,
        2015: 0.030,
        2020: 0.018,
        2022: 0.025,
        2024: 0.040,
        2025: 0.038,
    }
    base_rate = rate_by_year.get(orig_year, 0.030)
    interest_rate = max(0.001, float(rng.normal(base_rate, 0.005)))
    interest_rate = min(interest_rate, 0.099)

    # Borrower + affordability
    borrower_pool = list(BorrowerType)
    borrower_type = borrower_pool[
        int(rng.choice(len(borrower_pool), p=[0.25, 0.55, 0.20]))
    ]
    income = float(rng.normal(75_000, 25_000))
    gross_household_income = max(25_000.0, round(income, 2))
    partner_income_included = bool(rng.random() < 0.55)
    student_loan_debt = round(max(0.0, float(rng.normal(8_000, 12_000))), 2)
    bkr_pool = list(BkrScoreBand)
    bkr_band = bkr_pool[int(rng.choice(len(bkr_pool), p=[0.55, 0.25, 0.12, 0.06, 0.02]))]
    bkr_neg = bool(bkr_band in {BkrScoreBand.D, BkrScoreBand.E})
    # DSCR ~ income / annual debt service; rough proxy
    annual_debt_service = current_balance * (interest_rate + 0.02)
    dscr = round(
        gross_household_income / max(annual_debt_service, 1.0), 3
    )

    # Credit-risk metrics
    pd_12m = round(float(np.clip(rng.beta(2, 250), 0.0001, 0.20)), 6)
    pd_lifetime = round(float(np.clip(pd_12m * float(rng.uniform(3, 8)), pd_12m, 0.6)), 6)
    # LGD: lower if NHG, else from current LTV
    ltv_current_proxy = current_balance / max(property_value_current, 1.0)
    if nhg_flag:
        lgd = round(float(np.clip(rng.normal(0.02, 0.01), 0.0, 0.05)), 4)
    else:
        # Piecewise: at low LTV minimal LGD; above 90% steep
        lgd_base = max(0.0, (ltv_current_proxy - 0.6)) * 0.5
        lgd = round(float(np.clip(rng.normal(lgd_base, 0.03), 0.0, 0.7)), 4)
    ead = current_balance

    # Most loans Stage 1; small fraction Stage 2/3
    stage_roll = rng.random()
    if stage_roll < 0.92:
        ifrs9_stage = IFRS9Stage.ONE
        days_past_due = 0
        arrears_bucket = ArrearsBucket.ZERO
        restructured_flag = False
        unlikely_to_pay_flag = False
        sicr_trigger = SicrTrigger.NONE
    elif stage_roll < 0.98:
        ifrs9_stage = IFRS9Stage.TWO
        days_past_due = int(rng.integers(0, 60))
        arrears_bucket = (
            ArrearsBucket.BUCKET_31_60 if days_past_due > 30 else ArrearsBucket.ZERO
        )
        restructured_flag = bool(rng.random() < 0.30)
        unlikely_to_pay_flag = False
        sicr_trigger = SicrTrigger.QUANT_PD_INCREASE
    else:
        ifrs9_stage = IFRS9Stage.THREE
        days_past_due = int(rng.integers(90, 200))
        arrears_bucket = ArrearsBucket.NINETY_PLUS
        restructured_flag = bool(rng.random() < 0.40)
        unlikely_to_pay_flag = bool(rng.random() < 0.5)
        sicr_trigger = SicrTrigger.DPD_30_BACKSTOP
        if not (days_past_due >= 90 or unlikely_to_pay_flag or restructured_flag):
            # Schema invariant: ensure at least one Stage 3 backstop holds
            unlikely_to_pay_flag = True

    # Basel risk weight — IRB-style proxy
    if nhg_flag:
        risk_weight = round(float(np.clip(rng.normal(0.08, 0.02), 0.02, 0.20)), 4)
    else:
        risk_weight = round(
            float(np.clip(rng.normal(0.35 + 0.6 * pd_lifetime, 0.08), 0.05, 1.0)), 4
        )

    return {
        "loan_id": f"LN-{id_prefix}-{idx:06d}",
        "borrower_id": f"BO-{id_prefix}-{idx // 3:05d}",
        "borrower_type": borrower_type.value,
        "origination_date": origination,
        "maturity_date": maturity,
        "original_principal": original_principal,
        "current_balance": current_balance,
        "interest_rate": round(interest_rate, 6),
        "rate_type": rate_type.value,
        "rentevast_einddatum": rentevast_einddatum,
        "repayment_type": repayment_type.value,
        "tax_deduction_eligible": tax_deduction_eligible,
        "hra_phase_out_rate": round(hra_phase_out_rate, 6),
        "interest_only_portion": interest_only_portion,
        "currency": "EUR",
        "property_value_at_origination": property_value_at_origination,
        "taxatie_waarde": taxatie_waarde,
        "taxatie_date": taxatie_date,
        "taxatie_type": taxatie_type.value,
        "woz_waarde": woz_waarde,
        "woz_reference_date": woz_reference_date,
        "property_value_current": property_value_current,
        "pc6": pc6,
        "gemeente": gemeente,
        "property_type": property_type.value,
        "bouwjaar": bouwjaar,
        "energy_label": energy_label.value,
        "nhg_flag": nhg_flag,
        "nhg_cap_at_origination": nhg_cap,
        "nhg_premium_paid": nhg_premium,
        "pd_12m": pd_12m,
        "pd_lifetime": pd_lifetime,
        "lgd": lgd,
        "ead": ead,
        "ifrs9_stage": ifrs9_stage.value,
        "sicr_trigger_reason": sicr_trigger.value,
        "days_past_due": days_past_due,
        "arrears_bucket": arrears_bucket.value,
        "restructured_flag": restructured_flag,
        "watchlist_flag": False,
        "unlikely_to_pay_flag": unlikely_to_pay_flag,
        "risk_weight": risk_weight,
        "gross_household_income": gross_household_income,
        "partner_income_included": partner_income_included,
        "student_loan_debt": student_loan_debt,
        "bkr_score_band": bkr_band.value,
        "bkr_negative_registration_flag": bkr_neg,
        "dscr": dscr,
    }


# ---------------------------------------------------------------------------
# Easter-egg injection
# ---------------------------------------------------------------------------


def _inject_easter_eggs(
    rows: list[dict[str, object]], rng: np.random.Generator
) -> list[dict[str, object]]:
    """Stamp 4 named anomaly cohorts onto an existing tape.

    Idempotent on the row order; mutates rows in place and returns them.
    Each row gets an ``easter_egg`` field whose value is None or the egg key.
    """
    for r in rows:
        r["easter_egg"] = None

    n = len(rows)
    if n < 30:
        return rows  # too few rows to seed meaningfully

    # 1. HIGH_AFLOSSINGSVRIJ_COHORT — pick a single vintage year, force
    #    AFLOSSINGSVRIJ on ~10 rows in that vintage.
    vintage_year_idx = int(rng.integers(0, n))
    target_year = rows[vintage_year_idx]["origination_date"].year  # type: ignore[union-attr]
    cohort_picks = [i for i, r in enumerate(rows) if r["origination_date"].year == target_year][:10]  # type: ignore[union-attr]
    for i in cohort_picks:
        r = rows[i]
        r["repayment_type"] = RepaymentType.AFLOSSINGSVRIJ.value
        r["tax_deduction_eligible"] = False
        r["interest_only_portion"] = round(float(r["original_principal"]) * 0.95, 2)  # type: ignore[arg-type]
        r["easter_egg"] = EasterEgg.HIGH_AFLOSSINGSVRIJ_COHORT.value

    # 2. STALE_TAXATIE_CLUSTER — pick rows in one PC4 prefix, age taxatie_date
    #    > 36 months past origination.
    target_pc4 = rows[int(rng.integers(0, n))]["pc6"][:4]  # type: ignore[index]
    stale_picks = [i for i, r in enumerate(rows) if r["pc6"][:4] == target_pc4 and r["easter_egg"] is None][:8]  # type: ignore[index]
    for i in stale_picks:
        r = rows[i]
        orig = r["origination_date"]
        r["taxatie_date"] = orig - timedelta(days=365 * 4)  # type: ignore[operator]
        r["easter_egg"] = EasterEgg.STALE_TAXATIE_CLUSTER.value

    # 3. NHG_CAP_BREACH_BATCH — small batch where nhg_flag=True
    #    AND original_principal > nhg_cap_at_origination.
    breach_picks = [
        i for i, r in enumerate(rows) if r["easter_egg"] is None
    ][:5]
    for i in breach_picks:
        r = rows[i]
        r["nhg_flag"] = True
        cap = float(r["nhg_cap_at_origination"])  # type: ignore[arg-type]
        r["original_principal"] = round(cap * 1.15, 2)
        # Rebuild dependent fields to keep LGD/risk-weight roughly sane
        r["current_balance"] = min(float(r["current_balance"]), float(r["original_principal"]))  # type: ignore[arg-type]
        r["easter_egg"] = EasterEgg.NHG_CAP_BREACH_BATCH.value

    # 4. HIGH_INTEREST_ONLY_CLUSTER — interest_only_portion > 50% of
    #    property_value_at_origination on HRA-eligible loans.
    io_picks = [
        i for i, r in enumerate(rows)
        if r["easter_egg"] is None and r["tax_deduction_eligible"]
    ][:6]
    if not io_picks:
        # Fallback if all eligible loans were already flagged
        io_picks = [i for i, r in enumerate(rows) if r["easter_egg"] is None][:6]
    for i in io_picks:
        r = rows[i]
        r["interest_only_portion"] = round(
            float(r["property_value_at_origination"]) * 0.65, 2  # type: ignore[arg-type]
        )
        r["easter_egg"] = EasterEgg.HIGH_INTEREST_ONLY_CLUSTER.value

    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DATE_COLS: tuple[str, ...] = (
    "origination_date",
    "maturity_date",
    "rentevast_einddatum",
    "taxatie_date",
    "woz_reference_date",
)


def _loan_id_prefix(seed: int) -> str:
    """Stable 4-char prefix derived from the seed so different seeds get
    different loan_id sets while same seed remains deterministic."""
    return f"{abs(seed) % 10000:04d}"


def generate_tape(
    n: int,
    seed: int,
    inject_easter_eggs: bool = True,
) -> pl.DataFrame:
    """Generate a synthetic Dutch mortgage tape of ``n`` loans.

    Pure function: same ``(n, seed, inject_easter_eggs)`` → identical DataFrame.
    Every row satisfies the ``Loan`` Pydantic schema.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    rng = np.random.default_rng(seed)
    prefix = _loan_id_prefix(seed)
    rows = [_generate_row(rng, idx, id_prefix=prefix) for idx in range(n)]
    if inject_easter_eggs:
        rows = _inject_easter_eggs(rows, rng)
    else:
        for r in rows:
            r["easter_egg"] = None
    df = pl.from_dicts(rows)
    # Polars infers Python ``date`` as Date; nothing more to do.
    return df


def validate_tape(df: pl.DataFrame) -> int:
    """Reconstruct every row as a ``Loan`` to confirm schema conformance.

    Returns the number of successfully constructed Loans. Raises on the first
    failure — caller can wrap in try/except for fail-gracefully reporting.
    """
    payload_cols = [c for c in df.columns if c != "easter_egg"]
    count = 0
    for row in df.select(payload_cols).to_dicts():
        Loan(**row)
        count += 1
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Dutch synthetic loan tape.")
    parser.add_argument("--n", type=int, default=10_000, help="Number of loans.")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed.")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "data" / "samples" / "synthetic_tape_v1.parquet",
        help="Output Parquet path.",
    )
    parser.add_argument(
        "--no-easter-eggs",
        action="store_true",
        help="Skip seeded anomaly cohorts (cleaner tape for baselines).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="After generation, reconstruct every row through Pydantic.",
    )
    args = parser.parse_args(argv)

    tape = generate_tape(
        n=args.n,
        seed=args.seed,
        inject_easter_eggs=not args.no_easter_eggs,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    tape.write_parquet(args.out)
    print(f"Wrote {tape.shape[0]} loans to {args.out}")

    if args.validate:
        ok = validate_tape(tape)
        print(f"Validated {ok}/{tape.shape[0]} rows through Pydantic schema.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
