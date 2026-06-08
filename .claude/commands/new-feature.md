---
description: Scaffold a new feature with plan, failing test, impl stub, and eval rubric placeholder. Refuses if no plan exists.
---

# /new-feature <name>

Scaffold a new feature under `src/loan_tape/` following TDD discipline.

## Procedure

1. **Refuse without a plan.** If `.claude/plans/YYYY-MM-DD-<name>.md` does not exist, write one first. The plan must include: goal, regulatory anchor, schema fields touched, eval impact, test cases.

2. **Detect regulated path.** If the feature lives in `src/loan_tape/ecl/`, `src/loan_tape/analytics/stress.py`, `src/loan_tape/validate/rules.py`, or `evals/rubrics/`, add a `2nd-line-required` note to the plan and a checklist item in the eventual PR.

3. **Scaffold:**
   - `src/loan_tape/<area>/<name>.py` — module with a TODO header, no logic.
   - `tests/unit/<area>/test_<name>.py` — at least one failing test stub.
   - `evals/rubrics/<name>.md` — placeholder rubric if regulated path.
   - Append entry to `docs/governance/model-inventory.md` if introducing a new quantitative rule.

4. **Print next steps:**
   - "Write the failing test."
   - "Run `pytest tests/unit/<area>/test_<name>.py -x` and confirm RED."
   - "Implement minimum code to make it GREEN."
   - "Refactor."
   - "Commit with `[ai-assisted]` trailer."

## Anti-patterns

- Scaffolding without a plan file → refuse.
- Scaffolding an impl file without a test file → refuse.
- Scaffolding under a regulated path without flagging 2nd-line → refuse.

## Reference

- `.claude/skills/write-test-first.md`
- `.claude/skills/add-validation-rule.md` (if validation rule)
- `.claude/skills/add-stress-scenario.md` (if stress scenario)
- `.claude/skills/add-sicr-trigger.md` (if SICR trigger)
- `.claude/skills/add-anomaly-detector.md` (if anomaly detector)
