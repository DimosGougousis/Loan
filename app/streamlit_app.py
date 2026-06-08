"""Dutch Synthetic Loan-Tape Analyzer — Streamlit entry point.

Run with::

    uv run streamlit run app/streamlit_app.py

The sidebar provides a tape-picker shared across all pages. Tape selection is
stored in ``st.session_state['tape_id']`` and the loaded ``pl.DataFrame`` in
``st.session_state['tape']`` so individual pages can fetch via the helper
``app.shared.get_active_tape()``.
"""

from __future__ import annotations

import streamlit as st

from app.shared import (
    DEFAULT_TAPE_NAME,
    list_available_tapes,
    load_tape_into_state,
)


def main() -> None:
    st.set_page_config(
        page_title="Dutch Loan-Tape Analyzer",
        page_icon="🏠",
        layout="wide",
    )

    _sidebar()

    st.title("🏠 Dutch Synthetic Loan-Tape Analyzer")
    st.markdown(
        """
        **Portfolio piece** for the AI-Assisted Builder (Claude / AI Agents)
        role at a Dutch bank. Built end-to-end with Claude Code; harness in
        `.claude/`; governance docs in `docs/governance/`.

        Use the pages in the left sidebar:

        1. **Quick Scan** — portfolio at-a-glance KPIs
        2. **Portfolio Analysis** — vintage × arrears, concentration, LTV
        3. **Stress Testing** — DNB house-price, HRA phase-out, rate-reset,
           energy-label scenarios
        4. **Trend & Anomalies** — drift detection, isolation forest
        5. **Tape Validation** — schema + 9 NL cross-field rules + AnaCredit
        6. **Governance** — operations + AI-build governance dashboards
        """
    )

    with st.expander("About / Limits (EU AI Act Art. 13 — transparency)"):
        st.markdown(
            """
            **Purpose.** Portfolio-level analytics on a synthetic Dutch
            residential-mortgage tape.

            **Capabilities.** Quick scan, portfolio analysis, NL-tuned stress
            testing, trend & anomaly detection, loan-tape validation,
            governance dashboard.

            **Limits.**

            - Not a creditworthiness scoring system for natural persons
              (out of Annex III §5(b) scope).
            - Outputs are advisory; no automated downstream actions.
            - Synthetic data only — do not load production data without prior
              security review.
            - Built end-to-end with AI-assisted development; see
              `docs/governance/three-lines-of-defense.md` and
              `docs/eu-ai-act-position.md` for governance.
            """
        )


def _sidebar() -> None:
    """Render the tape-picker sidebar shared across pages."""
    with st.sidebar:
        st.header("Tape")
        tapes = list_available_tapes()
        if not tapes:
            st.warning(
                "No tapes found under `data/samples/`. Generate one with:\n"
                "`uv run python -m loan_tape.generator --seed 42 --n 10000 "
                "--out data/samples/synthetic_tape_v1.parquet`"
            )
            return

        default_index = 0
        if DEFAULT_TAPE_NAME in tapes:
            default_index = tapes.index(DEFAULT_TAPE_NAME)
        elif st.session_state.get("tape_id") in tapes:
            default_index = tapes.index(st.session_state["tape_id"])

        picked = st.selectbox(
            "Active tape",
            options=tapes,
            index=default_index,
            help="Parquet files under data/samples/",
        )
        if picked != st.session_state.get("tape_id"):
            load_tape_into_state(picked)
            st.session_state["tape_id"] = picked

        tape = st.session_state.get("tape")
        if tape is not None:
            st.caption(f"Loans: **{tape.shape[0]:,}**")
            st.caption(f"Columns: {tape.shape[1]}")

        st.divider()
        st.caption(
            "Synthetic data only. GDPR-clear. "
            "Not a creditworthiness scoring system."
        )


if __name__ == "__main__":
    main()
