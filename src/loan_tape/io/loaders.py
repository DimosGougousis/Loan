"""Tape loaders — read CSV or Parquet, optionally enforce schema at boundary.

Fail-gracefully contract (docs/governance/fail-gracefully.md §7.7.1 Ingest):

- File missing / wrong format → caller-friendly exception.
- Schema mismatch in strict mode → capture first ``max_issues`` violations,
  surface them in ``LoadResult.issues``; pipeline stage marked FAILED upstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import polars as pl
from pydantic import ValidationError

from loan_tape.schema import Loan

DEFAULT_MAX_ISSUES = 10


@dataclass(frozen=True)
class LoadIssue:
    """A single row-level validation issue surfaced by ``load_tape``."""

    row_index: int | None
    field: str | None
    message: str


@dataclass(frozen=True)
class LoadResult:
    """Outcome of loading a tape."""

    tape: pl.DataFrame
    path: Path
    row_count: int
    issues: list[LoadIssue] = field(default_factory=list)


def load_tape(
    path: Path,
    strict: bool = False,
    max_issues: int = DEFAULT_MAX_ISSUES,
) -> LoadResult:
    """Load a loan tape from disk.

    Supported formats: ``.parquet``, ``.csv``.

    Parameters
    ----------
    path:
        File path. Must exist; ``FileNotFoundError`` otherwise.
    strict:
        If True, reconstruct every row as ``Loan`` and capture the first
        ``max_issues`` validation issues. If False, return the raw DataFrame
        without schema enforcement (useful when reading from DuckDB views that
        were already validated at write time).
    max_issues:
        Cap on captured issues per fail-gracefully §7.7.1.
    """
    if not path.exists():
        raise FileNotFoundError(f"Tape not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".parquet":
        tape = pl.read_parquet(path)
    elif suffix == ".csv":
        tape = pl.read_csv(path, try_parse_dates=True)
    else:
        raise ValueError(
            f"Unsupported tape extension {suffix!r} on {path}. "
            "Use .parquet or .csv."
        )

    issues: list[LoadIssue] = []
    if strict:
        payload_cols = [c for c in tape.columns if c != "easter_egg"]
        for i, row in enumerate(tape.select(payload_cols).to_dicts()):
            try:
                Loan(**row)
            except ValidationError as exc:
                # First error from the row is enough; full chain is in exc.errors().
                first = exc.errors()[0]
                issues.append(
                    LoadIssue(
                        row_index=i,
                        field=".".join(str(p) for p in first.get("loc", [])) or None,
                        message=first.get("msg", "schema violation"),
                    )
                )
                if len(issues) >= max_issues:
                    break
            except (TypeError, KeyError) as exc:  # required field missing
                issues.append(
                    LoadIssue(
                        row_index=i,
                        field=None,
                        message=f"row construction failed: {exc!s}",
                    )
                )
                if len(issues) >= max_issues:
                    break

    return LoadResult(
        tape=tape,
        path=path,
        row_count=tape.shape[0],
        issues=issues,
    )
