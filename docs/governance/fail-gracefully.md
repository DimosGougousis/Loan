# Fail-Gracefully Playbook

> Every failure mode in the platform and the build pipeline has a contracted behavior: halt cleanly, log structured, surface to the right line, never silently degrade. This document is the spec. Implement to it, do not improvise error handling.

## Principles

1. **Every failure is named.** No generic "error" — every code path has a labeled failure mode.
2. **Every failure has a line owner.** 1st-line, 2nd-line, or IT — never ambiguous.
3. **No stage silently advances.** A stage `FAILED` or `BLOCKED` stays that way until an explicit human override.
4. **Every degraded-mode run is flagged on the report.** "We fell back to rule-based anomaly detection because isolation forest didn't converge" — surfaced, not hidden.

---

## §7.7.1 — Data pipeline (per tape run)

| Stage | Failure mode | Graceful behavior |
|---|---|---|
| 1. Ingest | File missing / unreadable / wrong format | Mark stage `FAILED`. Render upload error with file hash + expected schema. **Do not** advance to stage 2. |
| 1. Ingest | Schema mismatch (new column / wrong type / out-of-range) | Pydantic raises. Capture first 10 violations to `pipeline_runs.error_payload`. Surface: *"Schema drift detected — owner: 1st line"*. |
| 2. Validation | > 1% rows fail critical rules | Mark stage `BLOCKED`. Do **not** auto-advance. Require 1st-line override with comment. Override logged to `decisions.md`. |
| 2. Validation | AnaCredit-required attribute null | Stage proceeds with `WARNING`. Flagged in report. Cannot reach `Publish` without resolution. |
| 3. Quick Scan | Computation OK but produces NaN/Inf | Stage marked `FAILED`. Root cause traced to specific field. **Never** displayed as "0.0". |
| 4. Portfolio Analysis | Empty cohort (e.g., zero AFLOSSINGSVRIJ) | Render "no data for this segment" panel. **Do not crash the page.** |
| 5. Stress Testing | Scenario eval out-of-band (delta > 3× sanity bound) | Mark `FAILED`. Flag as "model behavior anomaly". Require 2nd-line review before advancing. |
| 6. Anomaly | Isolation forest fails to converge | Fall back to rule-based anomaly list. Log `degraded_mode=True` on the run. Report flagged. |
| 7. Sign-off | 2nd-line absent > 2 business days | Auto-escalate (Slack / email). Stage stays `BLOCKED`. **Never auto-approve.** |
| 8. Publish | DuckDB write fails | Retry with exponential backoff (3 attempts). On final failure, freeze state, **do not produce a partial report**. |
| ANY | Unhandled exception | Top-level handler writes structured incident record to `incidents/<id>.json`. Surfaces "something went wrong — incident ID X" to user. **Never raw stack trace.** |

---

## §7.7.2 — Build pipeline (per AI-assisted feature)

| Gate | Failure mode | Graceful behavior |
|---|---|---|
| 1. Planned | No plan file in `.claude/plans/` | `/new-feature` refuses to scaffold. |
| 2. Claude-implemented | Code written before test (TDD violation) | PreCommit hook detects: src diff without matching tests diff → **block commit** with instruction: *"Write the failing test first; this commit was refused per CLAUDE.md TDD rule"*. |
| 2. Claude-implemented | AI commit missing `[ai-assisted]` trailer | PreCommit hook blocks commit. |
| 2. Claude-implemented | AI commit > 500 changed lines | PreCommit hook blocks. Requires explicit human re-affirmation (split or `--allow-mass-rewrite` flag with reason). |
| 3. Tests green | Test failure on PR | CI red. Merge blocked. Failure summary posted as PR comment. |
| 4. Evals green | Eval rubric fails | CI red. Eval delta vs. baseline shown in PR comment. Merge blocked. |
| 4. Evals green | Eval flaky (passes 4/5 reruns) | CI marks `FLAKY`. Merge requires 2nd-line override with reasoning logged in `decisions.md`. |
| 5. 1st-line review | Reviewer requests changes | Standard PR loop. |
| 6. 2nd-line review | Reviewer rejects | Feature returns to gate 2. Rejection rationale logged in `decisions.md`. |
| 6. 2nd-line review | Reviewer absent > SLA | Auto-escalate. **Never bypass. No auto-merge of 2nd-line-gated paths under any condition.** |
| 7. Merged | Post-merge eval regression detected nightly | Automatic rollback PR opened. Incident filed. Production deploy paused. |
| 8. Deployed | Streamlit app fails health check | Previous version stays live. Deploy marked `FAILED`. Incident filed. **No traffic served from broken version.** |
| ANY | Claude generates mass-delete or mass-rewrite | PreCommit flags diff > 500 lines. Human re-affirmation required. |
| ANY | Secret detected in diff | `precommit_secrets.py` blocks commit (wraps detect-secrets). |

---

## Severity → action matrix

| Severity | Pipeline action | Build action | Who is paged |
|---|---|---|---|
| CRITICAL | Stage `FAILED`, blocks Publish | Merge blocked | 1st line immediately; 2nd line if regulated |
| HIGH | Stage `WARNING`, advances with flag | Merge requires override comment | 1st line same business day |
| MEDIUM | Surfaces in report | Logged as PR comment | 1st line next standup |
| LOW | Surfaces in report appendix | Logged | None |

## Anti-patterns this playbook prevents

- Silent stage advancement after a failure.
- Returning "0" when a calculation produced NaN.
- Auto-approving 2nd-line gates when the reviewer is slow.
- Catching `Exception` broadly and hiding the cause.
- AI-generated mass-rewrites slipping through code review.
- Validation reports without an audit hash.
- Stack traces leaking to end users.

## See also

- `docs/governance/three-lines-of-defense.md` — who owns what
- `docs/governance/change-management.md` — gate enforcement
- `.claude/CLAUDE.md` — Iron Law and TDD discipline
