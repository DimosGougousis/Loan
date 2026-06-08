"""Dutch Synthetic Loan-Tape Analyzer — Streamlit entry point.

Run with::

    uv run streamlit run app/streamlit_app.py

TODO Day 1 EVE: implement sidebar tape-picker, About/Limits panel (EU AI Act Art. 13),
and lazy page loading.
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="Dutch Loan-Tape Analyzer",
        page_icon="🏠",
        layout="wide",
    )

    st.title("🏠 Dutch Synthetic Loan-Tape Analyzer")
    st.markdown(
        """
        **Portfolio piece — Day 0 bootstrap.** Schema and pages will be populated
        during Days 1–3 of the build sequence.

        - Synthetic data only — no PII, no DPIA required (GDPR-clear).
        - Built with Claude Code; harness in `.claude/`.
        - Governance: `docs/governance/three-lines-of-defense.md`.
        - EU AI Act position: `docs/eu-ai-act-position.md`.

        See sidebar (left) for navigation once pages land.
        """
    )

    with st.expander("About / Limits (per EU AI Act Art. 13 — transparency)"):
        st.markdown(
            """
            **Purpose.** Portfolio-level analytics on a synthetic Dutch residential-mortgage tape.

            **Capabilities.** Quick scan, portfolio analysis, NL-tuned stress testing,
            trend & anomaly detection, loan-tape validation, governance dashboard.

            **Limits.**
            - Not a creditworthiness scoring system for natural persons (out of Annex III §5(b) scope).
            - Outputs are advisory; no automated downstream actions.
            - Synthetic data only; do not load production loan data without prior security review.
            - Built end-to-end with AI-assisted development; see `docs/governance/three-lines-of-defense.md`
              and `docs/eu-ai-act-position.md` for governance.
            """
        )


if __name__ == "__main__":
    main()
