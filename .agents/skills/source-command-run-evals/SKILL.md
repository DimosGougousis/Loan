---
name: "source-command-run-evals"
description: "Execute all eval rubrics, write a dated report under evals/results/, surface pass/fail per rubric."
---

# source-command-run-evals

Use this skill when the user asks to run the migrated source command `run-evals`.

## Command Template

# /run-evals

Run the eval suite and report.

## Procedure

1. Execute `uv run python evals/runner.py`.
2. The runner discovers every `evals/rubrics/*.md` and pairs it with the corresponding pytest case under `tests/` (matched by name).
3. For each rubric: run, capture pass/fail, eval delta vs. last recorded value.
4. Write a dated report to `evals/results/<YYYY-MM-DD-HHMMSS>.md` with sections:
   - Summary (pass count / fail count / flaky count)
   - Per-rubric detail (name, status, delta, notable findings)
   - Regression alerts (any rubric that regressed since last run)

5. If any rubric fails:
   - Print the offending output.
   - Exit non-zero.
   - Surface the failure as a `gate_failure` row in `governance_state.duckdb` for the dashboard.

6. If a regulated-path rubric (stress, sicr, validation) is missing or stale (last run > 7 days), warn and exit non-zero.

## Iron Law

This command is the verification step for evals. After running, **read the report**. Do not claim "evals green" because the command exited 0 — open the file and confirm the per-rubric details.

## Reference

- `.Codex/skills/verify-before-claim.md`
- `evals/runner.py`
