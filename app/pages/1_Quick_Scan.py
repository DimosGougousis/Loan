"""Quick Scan page — portfolio KPIs at-a-glance.

Reads the active tape from session_state (set by the sidebar tape-picker in
``app/streamlit_app.py``). Defers every metric calculation to
``loan_tape.analytics.quick_scan`` so the same logic runs in CLI / Streamlit
/ tests.
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.shared import get_active_tape
from loan_tape.analytics.quick_scan import compute_quick_scan, vintage_histogram

st.set_page_config(page_title="Quick Scan — Dutch Loan-Tape", page_icon="📊", layout="wide")
st.title("📊 Quick Scan")

tape = get_active_tape()
if tape is None:
    st.warning("Pick a tape in the sidebar.")
    st.stop()

with st.expander("About this page (EU AI Act Art. 13 — transparency)"):
    st.markdown(
        """
        Portfolio-level KPIs computed on the active tape. Every number is
        **advisory** — there are no automated downstream actions.

        Metrics defined in `src/loan_tape/analytics/quick_scan.py`; the same
        functions are exercised by unit tests on the pinned golden fixture.
        """
    )

kpis = compute_quick_scan(tape)

# ----- Summary cards ---------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Loans", f"{kpis.loan_count:,}")
col2.metric("Borrowers", f"{kpis.borrower_count:,}")
col3.metric("Total exposure", f"€ {kpis.total_exposure:,.0f}")
col4.metric("NHG share", f"{kpis.nhg_share * 100:.1f}%")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Weighted avg PD 12m", f"{kpis.weighted_avg_pd_12m * 100:.3f}%")
col6.metric("Weighted avg PD lifetime", f"{kpis.weighted_avg_pd_lifetime * 100:.2f}%")
col7.metric("Weighted avg current LTV", f"{kpis.weighted_avg_current_ltv * 100:.1f}%")
col8.metric(
    "Aflossingsvrij share",
    f"{kpis.aflossingsvrij_share * 100:.1f}%",
    help="Share of loans with interest-only repayment type",
)

# ----- Stage mix + Energy label mix -----------------------------------------

st.markdown("### IFRS 9 stage mix")
stage_df = {
    "stage": list(kpis.ifrs9_stage_mix),
    "share": [v * 100 for v in kpis.ifrs9_stage_mix.values()],
}
fig_stage = px.bar(
    stage_df,
    x="stage",
    y="share",
    title="Share of loans by IFRS 9 stage (%)",
    color="stage",
    color_discrete_map={"1": "#15803d", "2": "#a16207", "3": "#b91c1c"},
)
fig_stage.update_layout(showlegend=False, yaxis_title="Share (%)")
st.plotly_chart(fig_stage, use_container_width=True)

st.markdown("### Energy label mix")
energy_df = {
    "label": list(kpis.energy_label_mix),
    "share": [v * 100 for v in kpis.energy_label_mix.values()],
}
fig_energy = px.bar(
    energy_df,
    x="label",
    y="share",
    title="Share of loans by energy label (%)",
)
fig_energy.update_layout(yaxis_title="Share (%)")
st.plotly_chart(fig_energy, use_container_width=True)

# ----- Vintage histogram -----------------------------------------------------

st.markdown("### Vintage distribution")
vint = vintage_histogram(tape)
fig_vint = px.bar(
    vint.to_pandas(),
    x="year",
    y="loan_count",
    title="Loan originations by year",
)
fig_vint.update_layout(yaxis_title="Loans")
st.plotly_chart(fig_vint, use_container_width=True)

# ----- HRA phase-out rate ----------------------------------------------------

st.caption(
    f"Weighted-average HRA phase-out rate across the book: "
    f"**{kpis.weighted_avg_hra_phase_out_rate * 100:.2f}%** "
    f"(Belastingdienst max 2025: 36.97%)."
)
