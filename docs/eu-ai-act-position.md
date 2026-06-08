# EU AI Act — Position Statement

> One-page answer to: *"Is this tool in scope of the EU AI Act, and if so, how do you comply?"*

## TL;DR

**This platform is portfolio-level analytics, not a high-risk AI system under Annex III §5(b).** It aggregates and visualizes already-computed PDs/LGDs/EADs; it does not score natural persons for creditworthiness. The Act's high-risk obligations do not directly bind this tool.

**However**, the platform voluntarily aligns to the spirit of Articles 9, 10, 13, 14, and 15 because (a) the underlying PD/LGD models *are* high-risk and the platform consumes their output, and (b) AI-assisted development practice falls under the bank's internal Responsible AI policy and DNB SAFEST guidance (2024).

## Risk classification

| Question | Answer |
|---|---|
| Does the system score natural persons for credit access (Annex III §5(b))? | **No.** Inputs are loan-level fields (PD/LGD/EAD) already computed by upstream models. |
| Does the system make or substantially influence individual decisions? | **No.** All outputs are advisory; no automated downstream action. |
| Is the system a general-purpose AI model? | **No.** It is bespoke analytics code, not a model. |
| Does it use AI agents to *build* the system? | **Yes** — Claude generates code under human review. This is a development practice, not a deployed AI system. |

**Conclusion:** Out of scope for high-risk obligations. In scope of voluntary good practice + internal policy + DNB SAFEST principles.

## Article mapping — concrete controls

Even at low residual risk, the build voluntarily aligns to the Act's spirit. Each article maps to a control already enforced in the harness:

| Article | What it asks | How the harness answers |
|---|---|---|
| **Art. 9** (risk management) | Continuous risk-management process | Eval suite runs on every PR. Failure blocks merge. `evals/rubrics/` is the risk register for quantitative rules. |
| **Art. 10** (data governance) | Data quality, representativeness, no contamination | Synthetic data only — no real loan data. Generator is deterministic and version-pinned. Tape hash logged on every published report. Reference tables (`data/reference/`) cite their public source. |
| **Art. 13** (transparency) | System purpose, capabilities, limits clear to users | README + in-app "About / Limits" panel on every Streamlit page. Every quantitative rule cites its source regulation. |
| **Art. 14** (human oversight) | Human-in-the-loop, ability to intervene | All Streamlit outputs are advisory. No automated downstream actions. AI-authored commits tagged `[ai-assisted]` and human-reviewed. Sign-off stage requires explicit 2nd-line approval — never auto-approved. |
| **Art. 15** (accuracy / robustness / cybersecurity) | Accuracy, robustness, security | pytest + evals on every PR (accuracy). PreCommit hooks: TDD guard, mass-rewrite guard, secrets scan (robustness + security). `detect-secrets` and dependency pinning. Fail-gracefully playbook covers every named failure mode (robustness). |

## DORA crosswalk (Reg 2022/2554)

DORA Art. 5–10 (ICT risk management) satisfied at a tool-portfolio level by:

| DORA element | This platform |
|---|---|
| Source control | Git, public GitHub repo. |
| CI gates | GitHub Actions runs ruff + pytest + evals + secrets on every PR. |
| Secrets scanning | `detect-secrets` baseline + CI job. |
| Dependency pinning | `pyproject.toml` with `>=` floors + `uv.lock` (after `uv sync`). |
| Restorability | Deterministic synthetic data + Parquet + DuckDB single-file backup. |
| Change management | `docs/governance/change-management.md` — approval gates, SemVer, hotfix path. |
| Incident logging | Structured incident records via the fail-gracefully playbook. |

## Internal AI-use policy alignment

The bank's internal Responsible AI policy and DNB SAFEST (2024) principles are addressed by:

- **Soundness** — eval suite + PreCommit guards.
- **Accountability** — `[ai-assisted]` trailer + 2nd-line approval gate.
- **Fairness** — no individual scoring; portfolio-level only.
- **Ethics** — bank policy out-of-scope here (synthetic data, no PII).
- **Skill** — `.claude/skills/` documents the build patterns; KT plan in role description.
- **Transparency** — every rule cites its regulation; model inventory is the disclosure.

## Maintenance

This position is reviewed:

- Annually by 2nd line.
- Whenever the EU AI Act adopts a delegated act or implementing regulation that touches credit analytics.
- Whenever DNB updates its AI guidance.

Update history in this section.

## See also

- `docs/governance/three-lines-of-defense.md`
- `docs/governance/model-inventory.md`
- `docs/governance/fail-gracefully.md`
- `docs/regulation-map.md`
