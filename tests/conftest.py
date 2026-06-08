"""Shared pytest fixtures.

The golden tape is the pinned 500-loan deterministic fixture used as the
input/output anchor for every analytics, validation, ECL, and stress test.
Its hash is pinned in ``tests/unit/test_golden_tape.py::GOLDEN_TAPE_SHA256``.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GOLDEN_TAPE_PATH = FIXTURES_DIR / "golden_tape.parquet"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repo root."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Absolute path to the test-fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def golden_tape_path() -> Path:
    """Path to the pinned 500-loan deterministic fixture.

    Fails fast if the fixture has not yet been written (regenerate via the
    CLI in ``loan_tape.generator``).
    """
    if not GOLDEN_TAPE_PATH.exists():
        pytest.skip(
            "golden_tape.parquet not yet generated — run: "
            "uv run python -m loan_tape.generator --seed 1 --n 500 "
            "--out tests/fixtures/golden_tape.parquet"
        )
    return GOLDEN_TAPE_PATH


@pytest.fixture(scope="session")
def golden_tape(golden_tape_path: Path) -> pl.DataFrame:
    """The pinned 500-loan tape loaded as a Polars DataFrame.

    Session-scoped — loaded once per pytest run. Downstream tests should treat
    this fixture as immutable; clone (``.clone()``) before mutating.
    """
    return pl.read_parquet(golden_tape_path)
