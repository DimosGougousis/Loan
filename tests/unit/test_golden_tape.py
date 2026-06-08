"""Golden tape regression tests.

The golden tape at ``tests/fixtures/golden_tape.parquet`` is a 500-loan
deterministic fixture generated with ``seed=1``. Its sha256 is pinned below.
Any change to the generator that shifts this hash is a deliberate breaking
change — bump the constant, document why in the commit, and re-pin every
analytics snapshot test that depends on the tape.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import polars as pl

from loan_tape.generator import generate_tape
from loan_tape.schema import Loan

GOLDEN_TAPE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "golden_tape.parquet"

#: Pinned hash. Bump only when the generator's behavior changes intentionally.
GOLDEN_TAPE_SHA256 = "130b86778a98d91b4701e7c86987bc29485c731918f2beb3a36cc14aeb82c4ce"

#: Generation parameters that produced the pinned hash.
#: The golden fixture is the CLEAN baseline (no easter eggs) — validation tests
#: that need anomalies generate their own injected tapes.
GOLDEN_TAPE_N = 500
GOLDEN_TAPE_SEED = 1
GOLDEN_TAPE_INJECT_EASTER_EGGS = False


def test_golden_tape_file_exists() -> None:
    """The pinned fixture must exist on disk so dependent tests can load it."""
    assert GOLDEN_TAPE_PATH.exists(), (
        f"{GOLDEN_TAPE_PATH} is missing. Regenerate with: "
        f"uv run python -m loan_tape.generator --seed {GOLDEN_TAPE_SEED} "
        f"--n {GOLDEN_TAPE_N} --out {GOLDEN_TAPE_PATH}"
    )


def test_golden_tape_sha256_pinned() -> None:
    """The stored fixture hashes to the pinned value."""
    actual = hashlib.sha256(GOLDEN_TAPE_PATH.read_bytes()).hexdigest()
    assert actual == GOLDEN_TAPE_SHA256, (
        "Golden tape hash drifted. If the generator change was intentional, "
        f"update GOLDEN_TAPE_SHA256 to {actual!r} and re-pin any analytics "
        "snapshot tests."
    )


def test_golden_tape_regenerates_identically() -> None:
    """Calling the generator with the same (n, seed) reproduces the stored frame."""
    fresh = generate_tape(
        n=GOLDEN_TAPE_N,
        seed=GOLDEN_TAPE_SEED,
        inject_easter_eggs=GOLDEN_TAPE_INJECT_EASTER_EGGS,
    )
    stored = pl.read_parquet(GOLDEN_TAPE_PATH)
    assert fresh.shape == stored.shape
    # Polars frame_equal handles column ordering and nulls correctly.
    assert fresh.equals(stored)


def test_golden_tape_all_rows_satisfy_schema() -> None:
    """Every row of the stored fixture round-trips through ``Loan``."""
    tape = pl.read_parquet(GOLDEN_TAPE_PATH)
    payload_cols = [c for c in tape.columns if c != "easter_egg"]
    loans = [Loan(**row) for row in tape.select(payload_cols).to_dicts()]
    assert len(loans) == GOLDEN_TAPE_N
