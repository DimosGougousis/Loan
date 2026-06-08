"""Shared Streamlit helpers — tape discovery, session-state loaders.

Stays free of Streamlit-only imports so the helpers are unit-testable.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = REPO_ROOT / "data" / "samples"
DEFAULT_TAPE_NAME = "synthetic_tape_v1.parquet"


def list_available_tapes(samples_dir: Path | None = None) -> list[str]:
    """Return sorted list of tape filenames under ``data/samples/``."""
    d = samples_dir or SAMPLES_DIR
    if not d.exists():
        return []
    return sorted(p.name for p in d.glob("*.parquet"))


def load_tape(name: str, samples_dir: Path | None = None) -> pl.DataFrame:
    """Load a tape by filename from ``data/samples/``."""
    d = samples_dir or SAMPLES_DIR
    return pl.read_parquet(d / name)


def load_tape_into_state(name: str) -> None:
    """Streamlit-only: stash the loaded tape in ``st.session_state['tape']``."""
    import streamlit as st

    st.session_state["tape_id"] = name
    st.session_state["tape"] = load_tape(name)


def get_active_tape() -> pl.DataFrame | None:
    """Return the currently active tape from ``st.session_state``, or None."""
    import streamlit as st

    tape = st.session_state.get("tape")
    if tape is None:
        active_name = st.session_state.get("tape_id") or DEFAULT_TAPE_NAME
        try:
            tape = load_tape(active_name)
            st.session_state["tape"] = tape
            st.session_state["tape_id"] = active_name
        except FileNotFoundError:
            return None
    return tape
