"""DuckDB store tests — persistence + query helpers (RED first)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from loan_tape.io.duckdb_store import (
    DuckDBStore,
)


@pytest.fixture
def store(tmp_path: Path) -> DuckDBStore:
    return DuckDBStore(tmp_path / "test.duckdb")


def test_store_persists_and_reloads_tape(
    store: DuckDBStore, golden_tape: pl.DataFrame
) -> None:
    store.write_tape(golden_tape, tape_id="golden")
    roundtrip = store.read_tape("golden")
    assert roundtrip.shape == golden_tape.shape
    assert set(roundtrip.columns) == set(golden_tape.columns)


def test_store_lists_registered_tapes(
    store: DuckDBStore, golden_tape: pl.DataFrame
) -> None:
    store.write_tape(golden_tape, tape_id="golden")
    store.write_tape(golden_tape.head(50), tape_id="small")
    listed = set(store.list_tapes())
    assert {"golden", "small"} <= listed


def test_store_query_by_vintage(
    store: DuckDBStore, golden_tape: pl.DataFrame
) -> None:
    """Vintage filter narrows the result set."""
    store.write_tape(golden_tape, tape_id="golden")
    expected = golden_tape.filter(
        pl.col("origination_date") >= date(2020, 1, 1)
    ).height
    got = store.query_by_vintage("golden", start=date(2020, 1, 1))
    assert got.shape[0] == expected


def test_store_query_by_ifrs9_stage(
    store: DuckDBStore, golden_tape: pl.DataFrame
) -> None:
    store.write_tape(golden_tape, tape_id="golden")
    expected_stage1 = golden_tape.filter(pl.col("ifrs9_stage") == "1").height
    got = store.query_by_stage("golden", stage="1")
    assert got.shape[0] == expected_stage1


def test_store_overwrites_on_repeated_write(
    store: DuckDBStore, golden_tape: pl.DataFrame
) -> None:
    store.write_tape(golden_tape, tape_id="overwrite_me")
    store.write_tape(golden_tape.head(10), tape_id="overwrite_me")
    roundtrip = store.read_tape("overwrite_me")
    assert roundtrip.shape[0] == 10


def test_store_read_missing_tape_raises(store: DuckDBStore) -> None:
    with pytest.raises(KeyError, match="not found"):
        store.read_tape("never-written")


def test_store_file_survives_close_and_reopen(
    tmp_path: Path, golden_tape: pl.DataFrame
) -> None:
    """A store closed and reopened still sees its tape — persistence is real."""
    path = tmp_path / "persist.duckdb"
    store1 = DuckDBStore(path)
    store1.write_tape(golden_tape.head(20), tape_id="persisted")
    store1.close()

    store2 = DuckDBStore(path)
    roundtrip = store2.read_tape("persisted")
    assert roundtrip.shape[0] == 20
    store2.close()
