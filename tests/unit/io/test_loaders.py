"""Loader tests — schema enforcement at the IO boundary (RED first)."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from loan_tape.io.loaders import (
    LoadIssue,
    LoadResult,
    load_tape,
)


def test_load_tape_reads_parquet_from_golden_fixture(golden_tape_path: Path) -> None:
    result = load_tape(golden_tape_path)
    assert isinstance(result, LoadResult)
    assert isinstance(result.tape, pl.DataFrame)
    assert result.tape.shape[0] == 500
    assert result.row_count == 500
    assert result.issues == []
    assert result.path == golden_tape_path


def test_load_tape_reads_csv(tmp_path: Path, golden_tape_path: Path) -> None:
    """CSV ingest works alongside Parquet."""
    csv_path = tmp_path / "tape.csv"
    pl.read_parquet(golden_tape_path).write_csv(csv_path)
    result = load_tape(csv_path)
    assert result.row_count == 500
    assert result.issues == []


def test_load_tape_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_tape(tmp_path / "no_such_tape.parquet")


def test_load_tape_raises_on_unknown_extension(tmp_path: Path) -> None:
    bogus = tmp_path / "tape.xls"
    bogus.write_bytes(b"not a tape")
    with pytest.raises(ValueError, match="Unsupported"):
        load_tape(bogus)


def test_load_tape_validates_schema_when_strict(
    tmp_path: Path, golden_tape_path: Path
) -> None:
    """strict=True reconstructs every row as Loan; clean tape -> no issues."""
    result = load_tape(golden_tape_path, strict=True)
    assert result.row_count == 500
    assert result.issues == []


def test_load_tape_captures_first_n_issues_in_strict_mode(tmp_path: Path) -> None:
    """A tape with bad rows surfaces the first ``max_issues`` violations and
    halts further validation (fail-gracefully §7.7.1: capture first 10)."""
    bad_tape = pl.DataFrame(
        {
            "loan_id": [f"LN-X-{i:04d}" for i in range(15)],
            # Deliberately omit required fields so every row fails schema.
        }
    )
    bad_path = tmp_path / "bad.parquet"
    bad_tape.write_parquet(bad_path)
    result = load_tape(bad_path, strict=True, max_issues=10)
    assert result.row_count == 15
    assert len(result.issues) == 10
    assert all(isinstance(issue, LoadIssue) for issue in result.issues)
    # Each issue references a row and includes a message.
    assert all(issue.row_index is not None for issue in result.issues)
    assert all(issue.message for issue in result.issues)


def test_load_tape_non_strict_skips_validation(tmp_path: Path) -> None:
    """strict=False loads raw without schema enforcement — useful for analytics
    that operate on already-validated DuckDB views."""
    bad_tape = pl.DataFrame(
        {"loan_id": ["LN-1", "LN-2"], "garbage": [1, 2]}
    )
    bad_path = tmp_path / "bad.parquet"
    bad_tape.write_parquet(bad_path)
    result = load_tape(bad_path, strict=False)
    assert result.row_count == 2
    assert result.issues == []
