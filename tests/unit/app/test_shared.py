"""Shared Streamlit helper tests — testable without Streamlit runtime."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from app.shared import list_available_tapes, load_tape


def test_list_available_tapes_returns_sorted_parquet_names(tmp_path: Path) -> None:
    (tmp_path / "b.parquet").write_bytes(b"")
    (tmp_path / "a.parquet").write_bytes(b"")
    (tmp_path / "c.txt").write_bytes(b"")  # non-parquet ignored
    out = list_available_tapes(tmp_path)
    assert out == ["a.parquet", "b.parquet"]


def test_list_available_tapes_handles_missing_dir(tmp_path: Path) -> None:
    assert list_available_tapes(tmp_path / "does_not_exist") == []


def test_load_tape_reads_parquet(tmp_path: Path, golden_tape: pl.DataFrame) -> None:
    golden_tape.write_parquet(tmp_path / "x.parquet")
    loaded = load_tape("x.parquet", samples_dir=tmp_path)
    assert loaded.shape == golden_tape.shape
