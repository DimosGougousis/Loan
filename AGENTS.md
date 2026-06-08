# Dutch Synthetic Loan-Tape Analyzer — Project Context

> Read this file first every session. It is the contract between you (Codex) and this project.

## What this is

A Dutch residential-mortgage loan-tape analytics platform: ingest a loan tape, validate it, surface KPIs, run NL-tuned stress scenarios, detect anomalies, and govern the whole process from a built-in dashboard. Built end-to-end with Codex as a portfolio piece for an AI-Assisted Builder role at a Dutch bank.

## The Iron Law

**Verify before claiming complete.** Run the command. Read the output. Check the exit code. Never write "should work" or "this is complete" without evidence. See `.Codex/skills/verify-before-claim.md`.

## Build discipline (non-negotiable)

1. **TDD always.** Failing test first → minimal code → green → refactor → commit. If code was written before a test, *delete the code and start over*. See `.Codex/skills/write-test-first.md`.
2. **One feature at a time.** Plan in `.Codex/plans/YYYY-MM-DD-<feature>.md`. Use `/new-feature` to scaffold.
3. **Small, named commits.** AI-authored commits MUST include the trailer `[ai-assisted]`. Enforced by PreCommit hook.
4. **Evals on regulated paths.** Any change under `src/loan_tape/ecl/`, `src/loan_tape/analytics/stress.py`, `src/loan_tape/validate/rules.py`, or `evals/rubrics/` requires an updated eval rubric and a 2nd-line review label on the PR before merge.

## The schema is the contract

`src/loan_tape/schema.py` (Pydantic v2) is the single source of truth for the Dutch mortgage tape. Every analytics function, validation rule, and eval reads from this schema. Never duplicate field definitions. When adding a field, update the schema, then the generator, then the validator, then the analytics, in that order.

See `docs/domain-primer.md` for the field-by-field rationale.

## Regulatory anchors

Every quantitative rule must cite its source: IFRS 9 / EBA GL / DNB guidance / Basel / AnaCredit / NHG / *Tijdelijke regeling hypothecair krediet* / Nibud. Document it in `docs/regulation-map.md` and `docs/governance/model-inventory.md` when the rule lands.

## Governance lens

This is not a hobby project — it is an artifact a 2nd-line reviewer should be able to clear. Before opening a PR, run `/governance-check` and read `docs/governance/three-lines-of-defense.md` and `docs/eu-ai-act-position.md`. The fail-gracefully playbook (`docs/governance/fail-gracefully.md`) defines the contracted behavior for every pipeline and build-pipeline failure mode — implement to it, do not improvise.

## Folder map

| Path | Purpose |
|---|---|
| `src/loan_tape/` | Library code. Pure functions where possible. |
| `app/` | Streamlit UI. Thin — defers all logic to `src/`. |
| `data/` | Reference tables (NHG caps, HRA rates, Nibud LTI, PC6 lookup) + sample tapes. |
| `tests/` | `unit/` mirrors `src/` 1:1; `integration/` runs on golden tape; `fixtures/` is deterministic. |
| `evals/` | Rubrics + runner. `/run-evals` writes to `evals/results/<date>.md`. |
| `docs/` | Domain primer, regulation map, governance, EU AI Act position, build narrative. |
| `.Codex/` | Skills, slash commands, plans, hooks. The harness around Codex. |

## Tech stack (pinned)

Python 3.11 · uv · Polars (fallback pandas) · DuckDB · Pydantic v2 · Streamlit · Plotly · scikit-learn · statsmodels · pytest · hypothesis · ruff.

## When in doubt

- Open `docs/domain-primer.md` for Dutch mortgage context.
- Open `docs/governance/fail-gracefully.md` before designing any error path.
- Open `.Codex/skills/` for the procedure that matches your task.
- If no skill fits, *write one* before writing the code. The harness is part of the deliverable.
