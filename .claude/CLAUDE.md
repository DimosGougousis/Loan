# Harness Rules — `.claude/`

> This file complements the root `CLAUDE.md`. The root sets project context. This sets *how Claude operates inside this repo*.

## TDD is non-negotiable

Every code change follows red → green → refactor:

1. **Red.** Write the failing test first. Run it. See it fail with a clear error.
2. **Green.** Write the *minimum* code to make it pass. Run it. See it pass.
3. **Refactor.** Clean up while tests stay green.

**If you find yourself writing implementation code before a test exists — stop, `git checkout` the unfinished code, and start over with a test.** The PreCommit hook will catch this anyway, but catching it yourself is faster.

See `.claude/skills/write-test-first.md` for the procedure.

## Iron Law — verify before claiming complete

Before writing "done", "complete", or "this should work":

1. Identify the command that proves the claim (`pytest`, `streamlit run`, `/run-evals`, etc).
2. Run the **full** command.
3. Read the actual output. Check the exit code.
4. Only then make the claim.

"Should work", "looks correct", "the linter passed" are not evidence.

See `.claude/skills/verify-before-claim.md`.

## Commit conventions

All commits authored by Claude MUST include the trailer:

```
[ai-assisted]

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

The PreCommit hook (`precommit_ai_trailer.py`) refuses commits missing the trailer. This is the audit trail the governance dashboard reads to compute AI-authorship percentages.

Commit messages: imperative mood, under 72 chars subject, body explains *why*.

## src/ requires tests/

Any new module under `src/loan_tape/` MUST have a corresponding test file under `tests/unit/` with the same path. The PreCommit hook (`precommit_tdd_guard.py`) blocks commits violating this.

Example:
- Create `src/loan_tape/analytics/stress.py` → must also create `tests/unit/analytics/test_stress.py`.

## Regulated paths require 2nd-line review

Any change touching:

- `src/loan_tape/ecl/` (ECL / SICR)
- `src/loan_tape/analytics/stress.py`
- `src/loan_tape/validate/rules.py`
- `evals/rubrics/`

Requires:

1. Updated eval rubric (CI gate).
2. Updated `docs/governance/model-inventory.md` entry.
3. PR labeled `2nd-line-approved` before merge.

The governance dashboard Tab 2 makes this state visible.

## Mass-rewrite guard

No single AI-authored commit may change > 500 lines without explicit human re-affirmation. The PreCommit hook (`precommit_mass_rewrite_guard.py`) enforces this. If you need a large change, split it into focused commits.

## When something fails

Read `docs/governance/fail-gracefully.md` *first*. It defines the contracted behavior for every named failure mode in the data pipeline and build pipeline. Implement to the spec; do not improvise error handling.

## Schema is the contract

`src/loan_tape/schema.py` is the single source of truth for the Dutch mortgage tape. Add a field → update schema first, then generator, then validator, then analytics. Never duplicate field definitions.

## Skills before code

Before writing code for a task, check `.claude/skills/` for a matching procedure. If one matches, follow it. If none does and the task is non-trivial, *write the skill first* — the harness is part of the deliverable.

## Slash commands

- `/new-feature <name>` — scaffold plan + failing test + impl stub + eval placeholder
- `/run-evals` — execute eval rubrics, write report
- `/stress-run <scenario>` — run a stress scenario on the default tape
- `/tape-validate <file>` — full validation report
- `/governance-check` — checklist over the current diff
