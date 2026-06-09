# Architecture

> One-page system view. Filled in with a real graphviz diagram during Day 3.
>
> **Scope.** This document covers the *internals* of the platform — components, data flow, trust boundaries. For *where the platform sits in the broader Dutch mortgage ecosystem* (upstream origination, downstream consumers, and the rationale for our slice), see [`scope-boundary.md`](scope-boundary.md).

## Component diagram (graphviz DOT)

```dot
digraph LoanTapeAnalyzer {
    rankdir=LR;
    node [shape=box, style=rounded];

    // Inputs
    Tape [label="Loan Tape\n(Parquet / CSV)", shape=cylinder];
    RefData [label="Reference Data\n(NHG, HRA, Nibud)", shape=cylinder];

    // Library layer
    subgraph cluster_lib {
        label="src/loan_tape/ (library)";
        color=blue;

        Schema [label="schema.py\n(Pydantic v2)"];
        Loaders [label="io/loaders.py"];
        DuckDB [label="io/duckdb_store.py\n(.duckdb file)", shape=cylinder];
        Generator [label="generator.py\n(synthetic tape)"];
        Validate [label="validate/rules.py\nvalidate/anacredit.py"];
        Report [label="validate/report.py\n(HTML)"];
        IFRS9 [label="ecl/ifrs9.py\n(ECL)"];
        SICR [label="ecl/sicr.py\n(NL-tuned triggers)"];
        QuickScan [label="analytics/quick_scan.py"];
        Portfolio [label="analytics/portfolio.py"];
        Stress [label="analytics/stress.py\n(4 NL scenarios)"];
        Anomaly [label="analytics/anomaly.py"];
    }

    // UI layer
    subgraph cluster_app {
        label="app/ (Streamlit)";
        color=green;

        Page1 [label="1_Quick_Scan"];
        Page2 [label="2_Portfolio_Analysis"];
        Page3 [label="3_Stress_Testing"];
        Page4 [label="4_Trend_and_Anomalies"];
        Page5 [label="5_Tape_Validation"];
        Page6 [label="6_Governance\n(Tab 1 Ops + Tab 2 Build)"];
    }

    // Governance state
    GovDB [label="governance_state.duckdb\n(pipeline_runs + feature_runs + incidents)", shape=cylinder, color=orange];

    // Eval suite
    Evals [label="evals/rubrics/\n+ evals/runner.py", color=purple];

    // Edges — data path
    Tape -> Loaders -> Schema -> DuckDB;
    RefData -> Validate;
    DuckDB -> Validate -> Report;
    DuckDB -> IFRS9 -> SICR;
    DuckDB -> QuickScan -> Page1;
    DuckDB -> Portfolio -> Page2;
    DuckDB -> Stress -> Page3;
    DuckDB -> Anomaly -> Page4;
    Validate -> Page5;
    SICR -> Page2;

    // Edges — governance instrumentation
    Loaders -> GovDB [style=dashed, label="stage transitions"];
    Validate -> GovDB [style=dashed];
    QuickScan -> GovDB [style=dashed];
    Portfolio -> GovDB [style=dashed];
    Stress -> GovDB [style=dashed];
    Anomaly -> GovDB [style=dashed];
    Report -> GovDB [style=dashed, label="hash + audit"];
    GovDB -> Page6;

    // Eval gates
    Generator -> Evals [style=dotted];
    Validate -> Evals [style=dotted];
    SICR -> Evals [style=dotted];
    Stress -> Evals [style=dotted];
    Evals -> GovDB [style=dashed, label="pass/fail"];
}
```

To render: paste into `dot -Tpng` or upload to <https://dreampuf.github.io/GraphvizOnline/>.

## Data flow (sequence)

```
1. Analyst uploads tape via Streamlit (page 5).
2. loaders.py → Pydantic schema validation at boundary.
3. Tape persisted to DuckDB (single file under data/samples/).
4. validate/rules.py runs all cross-field rules → report.py → HTML.
5. analytics/* compute Quick Scan, Portfolio, Stress, Anomaly.
6. ecl/sicr.py determines IFRS 9 stage for each loan.
7. Pipeline stage transitions written to governance_state.duckdb.
8. Page 6 reads governance_state.duckdb → operations dashboard (Tab 1).
9. CI / GitHub Actions writes feature_runs entries → page 6 Tab 2.
10. Sign-off (Tab 1, 1st-line manual) → Publish (audit hash logged).
```

## Trust boundaries

- **External world** ↔ **Streamlit upload** — Pydantic schema enforces type/range at the boundary. No raw stack trace leaks back to user.
- **Library** ↔ **Governance state** — only writes through a typed wrapper; never raw DuckDB SQL from outside `io/`.
- **AI-authored code** ↔ **main branch** — PreCommit hooks + CI + 1st-line + 2nd-line (regulated paths only).

## Tech stack

Python 3.11 · uv · Polars + pandas fallback · DuckDB · Pydantic v2 · Streamlit · Plotly · scikit-learn · statsmodels · pytest + hypothesis · ruff · detect-secrets.

## See also

- `docs/domain-primer.md` — domain context behind the schema
- `docs/governance/fail-gracefully.md` — contracted failure behaviors per stage
- `docs/eu-ai-act-position.md` — trust boundary mapping to AI Act articles
