# Project Scope Presentation Plan

## Goal

Create an editable PowerPoint deck explaining the Dutch Synthetic Loan-Tape Analyzer scope across Requirements, Workflows, Checks, and Dashboards.

## Source Evidence

- `README.md` for target capabilities and positioning.
- `docs/architecture.md` for data flow, trust boundaries, and dashboard pages.
- `docs/domain-primer.md` for Dutch mortgage requirements.
- `docs/regulation-map.md` and `docs/eu-ai-act-position.md` for regulatory controls.
- `docs/governance/*.md` for 3LoD, RACI, change gates, and failure behavior.
- `app/streamlit_app.py`, `src/loan_tape/schema.py`, and `tests/unit/test_smoke.py` for current implementation status.

## Slides

1. Scope thesis and current-state caveat.
2. Requirements landscape.
3. Architecture and trust boundaries.
4. Analyst workflow.
5. Validation and regulatory checks.
6. Stress, SICR, and anomaly checks.
7. Governance and build gates.
8. Dashboard surface.
9. Implementation status and phased build-out.
10. Scope decision summary.

## Verification

- Export final PPTX through artifact-tool.
- Render all slides to PNG and generate a contact sheet.
- Confirm the PPTX exists, is non-empty, and contains 10 slides.
- Inspect rendered previews for visible layout, contrast, and overflow issues.
