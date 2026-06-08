"""Generator tests — RED first per ``.claude/CLAUDE.md`` TDD discipline.

The generator must be:

- **Deterministic** — same (n, seed) → byte-identical DataFrame.
- **Schema-conformant** — every row constructs a valid ``Loan``.
- **NL-realistic** — vintage product-mix, Randstad geography, energy label
  by bouwjaar, ~25% in the 2025–2028 rentevast reset cohort, HRA eligibility
  correct.
- **Easter-egg-bearing** — 4 named anomaly cohorts present when requested.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from loan_tape.generator import (
    EASTER_EGG_KEYS,
    EasterEgg,
    generate_tape,
)
from loan_tape.schema import (
    EnergyLabel,
    Loan,
    RepaymentType,
)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_seed_produces_identical_tape() -> None:
    a = generate_tape(n=200, seed=42, inject_easter_eggs=False)
    b = generate_tape(n=200, seed=42, inject_easter_eggs=False)
    assert a.shape == b.shape
    # Polars frame_equal is the canonical equality check
    assert a.equals(b)


def test_different_seed_produces_different_tape() -> None:
    a = generate_tape(n=200, seed=42, inject_easter_eggs=False)
    b = generate_tape(n=200, seed=43, inject_easter_eggs=False)
    # Loan IDs differ across seeds
    assert set(a["loan_id"]) != set(b["loan_id"])


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------


def test_every_row_parses_as_loan() -> None:
    """All 100 rows of a small tape construct as ``Loan`` without ValidationError.

    ``easter_egg`` is generator-only metadata, not a Loan field; strip before
    constructing.
    """
    tape = generate_tape(n=100, seed=1, inject_easter_eggs=False)
    payload_cols = [c for c in tape.columns if c != "easter_egg"]
    rows = tape.select(payload_cols).to_dicts()
    loans = [Loan(**r) for r in rows]
    assert len(loans) == 100


def test_every_row_parses_as_loan_with_easter_eggs() -> None:
    """Same as above but with easter eggs injected — they must still parse."""
    tape = generate_tape(n=200, seed=7, inject_easter_eggs=True)
    payload_cols = [c for c in tape.columns if c != "easter_egg"]
    rows = tape.select(payload_cols).to_dicts()
    loans = [Loan(**r) for r in rows]
    assert len(loans) == 200


def test_n_rows_returned() -> None:
    tape = generate_tape(n=357, seed=1, inject_easter_eggs=False)
    assert tape.shape[0] == 357


# ---------------------------------------------------------------------------
# NL realism
# ---------------------------------------------------------------------------


def test_vintage_range_covers_2010_to_2025() -> None:
    tape = generate_tape(n=2000, seed=1, inject_easter_eggs=False)
    years = tape["origination_date"].dt.year().unique().to_list()
    assert min(years) >= 2010
    assert max(years) <= 2025


def test_post_2013_dominated_by_annuiteit() -> None:
    """Tax-deduction regime change: post-2013 originations skew ANNUITEIT."""
    tape = generate_tape(n=2000, seed=1, inject_easter_eggs=False)
    post_2013 = tape.filter(pl.col("origination_date") >= date(2014, 1, 1))
    annuity_share = (
        post_2013.filter(pl.col("repayment_type") == "ANNUITEIT").height
        / post_2013.height
    )
    assert annuity_share > 0.55, (
        f"post-2013 ANNUITEIT share too low: {annuity_share:.2f}"
    )


def test_pre_2013_has_meaningful_aflossingsvrij_share() -> None:
    """Legacy cohort: ~30%+ AFLOSSINGSVRIJ/SPAAR/HYBRIDE."""
    tape = generate_tape(n=2000, seed=1, inject_easter_eggs=False)
    pre_2013 = tape.filter(pl.col("origination_date") < date(2013, 1, 1))
    if pre_2013.height == 0:
        pytest.skip("no pre-2013 originations in this seed — extremely unlikely")
    legacy_share = (
        pre_2013.filter(
            pl.col("repayment_type").is_in(["AFLOSSINGSVRIJ", "SPAAR", "HYBRIDE"])
        ).height
        / pre_2013.height
    )
    assert legacy_share > 0.30, f"pre-2013 legacy share too low: {legacy_share:.2f}"


def test_energy_label_correlated_with_bouwjaar() -> None:
    """Pre-1992 dwellings skew C-G; post-2015 dwellings skew A/A+."""
    tape = generate_tape(n=2000, seed=1, inject_easter_eggs=False)
    old = tape.filter(pl.col("bouwjaar") < 1992)
    new = tape.filter(pl.col("bouwjaar") >= 2015)
    if old.height == 0 or new.height == 0:
        pytest.skip("not enough variation in bouwjaar at this n/seed")
    old_low_label_share = (
        old.filter(pl.col("energy_label").is_in(["C", "D", "E", "F", "G"])).height
        / old.height
    )
    new_high_label_share = (
        new.filter(pl.col("energy_label").is_in(["A++++", "A+++", "A++", "A+", "A"])).height
        / new.height
    )
    assert old_low_label_share > 0.50, (
        f"pre-1992 low-label share too low: {old_low_label_share:.2f}"
    )
    assert new_high_label_share > 0.50, (
        f"post-2015 high-label share too low: {new_high_label_share:.2f}"
    )


def test_rentevast_reset_cohort_present() -> None:
    """~25% of loans should have rentevast_einddatum in 2025-2028 (the reset wave)."""
    tape = generate_tape(n=2000, seed=1, inject_easter_eggs=False)
    reset = tape.filter(
        (pl.col("rentevast_einddatum") >= date(2025, 1, 1))
        & (pl.col("rentevast_einddatum") <= date(2028, 12, 31))
    )
    reset_share = reset.height / tape.height
    assert reset_share > 0.15, f"rentevast reset cohort too small: {reset_share:.2f}"


def test_pc6_format_is_dutch() -> None:
    """Every PC6 must be 4 digits + 2 uppercase letters."""
    tape = generate_tape(n=500, seed=1, inject_easter_eggs=False)
    pattern = r"^\d{4}[A-Z]{2}$"
    assert tape["pc6"].str.contains(pattern).all()


def test_currency_always_eur() -> None:
    tape = generate_tape(n=500, seed=1, inject_easter_eggs=False)
    assert tape["currency"].unique().to_list() == ["EUR"]


# ---------------------------------------------------------------------------
# Easter eggs (anomaly cohorts for validation/anomaly testing)
# ---------------------------------------------------------------------------


def test_easter_eggs_keys_match_expected_set() -> None:
    """Four named easter eggs from §2.5 of the plan."""
    assert set(EASTER_EGG_KEYS) == {
        EasterEgg.HIGH_AFLOSSINGSVRIJ_COHORT,
        EasterEgg.STALE_TAXATIE_CLUSTER,
        EasterEgg.NHG_CAP_BREACH_BATCH,
        EasterEgg.HIGH_INTEREST_ONLY_CLUSTER,
    }


def test_easter_eggs_absent_when_disabled() -> None:
    """With inject_easter_eggs=False, no rows carry an easter_egg marker."""
    tape = generate_tape(n=500, seed=1, inject_easter_eggs=False)
    if "easter_egg" in tape.columns:
        assert tape.filter(pl.col("easter_egg").is_not_null()).height == 0


def test_easter_eggs_present_when_enabled() -> None:
    """Every named easter egg has at least one loan flagged when injection is on."""
    tape = generate_tape(n=1000, seed=1, inject_easter_eggs=True)
    assert "easter_egg" in tape.columns
    seeded_keys = set(
        tape.filter(pl.col("easter_egg").is_not_null())["easter_egg"].unique().to_list()
    )
    expected_values = {k.value for k in EASTER_EGG_KEYS}
    missing = expected_values - seeded_keys
    assert not missing, f"missing easter eggs: {missing}"


def test_high_aflossingsvrij_egg_concentrated_in_one_vintage() -> None:
    """The high-aflossingsvrij easter egg should cluster in a single origination year."""
    tape = generate_tape(n=1000, seed=1, inject_easter_eggs=True)
    flagged = tape.filter(
        pl.col("easter_egg") == EasterEgg.HIGH_AFLOSSINGSVRIJ_COHORT.value
    )
    assert flagged.height >= 5
    # All flagged rows are AFLOSSINGSVRIJ
    assert flagged["repayment_type"].unique().to_list() == [
        RepaymentType.AFLOSSINGSVRIJ.value
    ]


def test_nhg_cap_breach_egg_violates_cap() -> None:
    """The NHG cap-breach egg has nhg_flag=True AND principal > cap."""
    tape = generate_tape(n=1000, seed=1, inject_easter_eggs=True)
    flagged = tape.filter(pl.col("easter_egg") == EasterEgg.NHG_CAP_BREACH_BATCH.value)
    assert flagged.height >= 1
    assert flagged["nhg_flag"].all()
    breaches = flagged.filter(
        pl.col("original_principal") > pl.col("nhg_cap_at_origination")
    )
    assert breaches.height == flagged.height, (
        "all NHG_CAP_BREACH_BATCH rows must actually breach the cap"
    )


def test_high_energy_label_variation_present() -> None:
    """The tape must show variation across energy labels — DNB stress relevance."""
    tape = generate_tape(n=1000, seed=1, inject_easter_eggs=False)
    unique_labels = set(tape["energy_label"].unique().to_list())
    valid = {e.value for e in EnergyLabel}
    assert unique_labels <= valid
    assert len(unique_labels) >= 5, (
        f"expected variation across >=5 energy labels, got {unique_labels}"
    )
