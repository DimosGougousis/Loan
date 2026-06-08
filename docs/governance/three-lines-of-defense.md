# Three Lines of Defense — Platform Governance

> How the Dutch Synthetic Loan-Tape Analyzer is governed inside a typical Dutch retail bank.

## Purpose

This document maps the platform to a standard Dutch bank's 3LoD model. It is the answer to: *"Who owns what, who reviews what, who approves what, and who audits what?"* Read this before opening any PR that touches a regulated path.

## The three lines

| Line | Role | Owns | Reviews | Approves |
|---|---|---|---|---|
| **1st** | Credit Risk Portfolio Analytics team | Build, run, document the platform. Day-to-day use. Quality of inputs. | Own outputs before publishing to the business. | Feature merges to `main` within risk appetite. |
| **2nd** | Model Risk Management + Compliance | Independent challenge: methodology, assumptions, AI-build process integrity. | Every new stress scenario, SICR trigger, validation rule, eval rubric. | Production release. Material methodology changes. AI-assisted dev process. |
| **3rd** | Internal Audit | Periodic assurance over 1st and 2nd lines. | Annual audit of platform governance, change log, eval history, AI-Act conformance. | Audit opinion; recommendations. |

## DNB SAFEST alignment

DNB's 2024 *Guidance on the use of AI* sets six principles. Each maps to a concrete control in the harness:

| Principle | Concrete control |
|---|---|
| **S**oundness | Eval suite blocks merge on regression. PreCommit TDD guard. |
| **A**ccountability | `[ai-assisted]` commit trailer + 2nd-line sign-off gate on regulated paths. |
| **F**airness | Synthetic data; no individual scoring; tool is portfolio-level analytics. |
| **E**thics | Bank Responsible AI policy applies to development practice. |
| **S**kill | This document + the skills under `.claude/skills/`. |
| **T**ransparency | Every rule cites a regulation; model inventory is the disclosure. |

## Audit-ready artifacts

Internal Audit (3rd line) inspects, at minimum:

- `docs/governance/model-inventory.md` — every quantitative rule, its owner, version, eval, source regulation.
- `docs/governance/decisions.md` — every 2nd-line rejection or override.
- `evals/results/` — eval history.
- GitHub PR history — review labels, AI-authorship %, eval deltas.
- `governance_state.duckdb` — pipeline-run history with stage outcomes.

## See also

- `docs/governance/raci.md` — activity-level RACI
- `docs/governance/change-management.md` — approval gates and SemVer
- `docs/governance/fail-gracefully.md` — contracted failure behaviors
- `docs/eu-ai-act-position.md` — EU AI Act classification and Article mapping
