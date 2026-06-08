"""Shared pytest fixtures.

TODO Day 1 AM #3: implement ``golden_tape`` fixture loader once
``tests/fixtures/golden_tape.parquet`` is generated.
"""

from __future__ import annotations

from pathlib import Path

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

    Generated in Day 1 AM #3. Fails fast if the fixture has not yet been written.
    """
    if not GOLDEN_TAPE_PATH.exists():
        pytest.skip(
            "golden_tape.parquet not yet generated — run Day 1 AM #3 task first."
        )
    return GOLDEN_TAPE_PATH
