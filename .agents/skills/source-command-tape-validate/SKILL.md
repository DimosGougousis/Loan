---
name: "source-command-tape-validate"
description: "Run the full validation engine on a tape and produce an HTML report grouped by BCBS 239 dimension."
---

# source-command-tape-validate

Use this skill when the user asks to run the migrated source command `tape-validate`.

## Command Template

# /tape-validate <file>

Validate a loan tape end-to-end.

## Procedure

1. Load `<file>` (Parquet or CSV) through `src/loan_tape/io/loaders.py`.
2. Run Pydantic schema validation. Capture first 10 schema violations (no more — that is enough to act on).
3. Run all cross-field rules from `src/loan_tape/validate/rules.py::RULE_REGISTRY`.
4. Run AnaCredit conformance check via `src/loan_tape/validate/anacredit.py`.
5. Render an HTML report via `src/loan_tape/validate/report.py` with severity bands (CRITICAL / HIGH / MEDIUM / LOW) and BCBS 239 grouping (accuracy / completeness / timeliness / integrity).
6. Print summary: total issues, by severity, AnaCredit conformance %.
7. Write report to `docs/sample-reports/<tape-basename>-<YYYY-MM-DD>.html`.
8. Append row to `pipeline_runs` in `governance_state.duckdb`.

## Fail-gracefully

Per `docs/governance/fail-gracefully.md` §7.7.1:

- Schema mismatch → capture first 10 violations, surface "Schema drift detected — owner: 1st line", do not advance.
- > 1% rows fail critical → status `BLOCKED`, requires 1st-line override.
- AnaCredit required attribute null → status `WARNING`, blocks Publish.

Never silently return a partial report.

## Reference

- `.Codex/skills/add-validation-rule.md`
- `docs/governance/fail-gracefully.md`
