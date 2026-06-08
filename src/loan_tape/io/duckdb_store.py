"""DuckDB persistence — single-file SQL store that survives the bank's
security review (no infra, no network).

Each tape is registered as a named view over a Parquet payload stored alongside
the .duckdb file. Survives close/reopen because the payload is on disk.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import duckdb
import polars as pl


class DuckDBStore:
    """Single-file DuckDB store for loan tapes.

    Layout::

        <store-root>/
          test.duckdb         <- catalog (small)
          tapes/
            <tape_id>.parquet <- payload (large, content-addressed by tape_id)

    The catalog stores one row per ``tape_id`` in the ``tapes`` table:
    ``(tape_id TEXT PRIMARY KEY, path TEXT, written_at TIMESTAMP)``.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._payload_dir = self._path.parent / "tapes"
        self._payload_dir.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(self._path))
        self._ensure_catalog()

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    def _ensure_catalog(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tapes (
                tape_id TEXT PRIMARY KEY,
                payload_path TEXT NOT NULL,
                written_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def list_tapes(self) -> list[str]:
        rows = self._conn.execute("SELECT tape_id FROM tapes").fetchall()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def write_tape(self, tape: pl.DataFrame, tape_id: str) -> None:
        """Persist ``tape`` under ``tape_id``. Overwrites any existing entry.

        The payload Parquet file is written to ``tapes/<tape_id>.parquet`` and
        the catalog row is upserted. ``tape_id`` must be a safe filename (no
        path separators).
        """
        if "/" in tape_id or "\\" in tape_id:
            raise ValueError(f"tape_id may not contain path separators: {tape_id!r}")

        payload_path = self._payload_dir / f"{tape_id}.parquet"
        tape.write_parquet(payload_path)

        # DuckDB doesn't accept bare CURRENT_TIMESTAMP in UPSERT SET clauses
        # — wrap as get_current_timestamp() to disambiguate from a column ref.
        self._conn.execute(
            """
            INSERT INTO tapes (tape_id, payload_path, written_at)
                VALUES (?, ?, get_current_timestamp())
            ON CONFLICT (tape_id) DO UPDATE
              SET payload_path = excluded.payload_path,
                  written_at = get_current_timestamp()
            """,
            [tape_id, str(payload_path)],
        )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def _payload_for(self, tape_id: str) -> Path:
        row = self._conn.execute(
            "SELECT payload_path FROM tapes WHERE tape_id = ?", [tape_id]
        ).fetchone()
        if row is None:
            raise KeyError(f"tape_id {tape_id!r} not found in store")
        return Path(row[0])

    def read_tape(self, tape_id: str) -> pl.DataFrame:
        """Load a previously-written tape."""
        return pl.read_parquet(self._payload_for(tape_id))

    def query_by_vintage(
        self,
        tape_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Filter by ``origination_date`` window. Inclusive bounds."""
        path = self._payload_for(tape_id)
        sql_filter = []
        if start is not None:
            sql_filter.append(f"origination_date >= DATE '{start.isoformat()}'")
        if end is not None:
            sql_filter.append(f"origination_date <= DATE '{end.isoformat()}'")
        where = (" WHERE " + " AND ".join(sql_filter)) if sql_filter else ""
        arrow = self._conn.execute(
            f"SELECT * FROM read_parquet('{path.as_posix()}'){where}"
        ).arrow()
        return pl.from_arrow(arrow)  # type: ignore[return-value]

    def query_by_stage(self, tape_id: str, stage: str) -> pl.DataFrame:
        """Filter by IFRS 9 stage ('1', '2', or '3')."""
        path = self._payload_for(tape_id)
        arrow = self._conn.execute(
            f"SELECT * FROM read_parquet('{path.as_posix()}') "
            "WHERE ifrs9_stage = ?",
            [stage],
        ).arrow()
        return pl.from_arrow(arrow)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def drop(self) -> None:
        """Delete the store entirely (catalog + payloads). Test-only helper."""
        self.close()
        if self._path.exists():
            self._path.unlink()
        if self._payload_dir.exists():
            shutil.rmtree(self._payload_dir)
