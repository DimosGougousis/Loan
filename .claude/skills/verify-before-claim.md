---
name: verify-before-claim
description: The Iron Law. Use BEFORE writing "done", "complete", or "this should work" anywhere.
---

# Verify Before Claiming Complete

## The Iron Law

You may not claim a task is complete until you have:

1. **Identified** the exact command that proves the claim.
2. **Run** the full command, fresh.
3. **Read** the actual output and exit code.
4. **Verified** the output confirms the claim.

Skip any step → unverified. Unverified is not done.

## Forbidden phrases until verified

- "should work now"
- "this is complete"
- "the test should pass"
- "I'm confident"
- "the linter passed" (the linter is not the compiler)
- "the agent said success" (verify independently)

## Common verification commands

| Claim | Command |
|---|---|
| "Tests pass" | `uv run pytest -x` and read exit code |
| "Evals green" | `uv run python evals/runner.py` and read report |
| "App renders" | `uv run streamlit run app/streamlit_app.py` and load each page |
| "Coverage > 80%" | `uv run pytest --cov=src --cov-report=term` and read the number |
| "Validation catches issue X" | run validator on fixture containing X, check report |
| "Schema accepts/rejects field" | run Pydantic validation, check exception or success |
| "DuckDB persists" | open `.duckdb` file in a fresh process, query it back |
| "Hook fires" | trigger the hook condition, check side-effect |

## Rationalization detector

If you find yourself thinking any of these, stop and verify:

| Thought | Reality |
|---|---|
| "It's just a tiny change" | Tiny changes still need to pass tests |
| "I just renamed a variable" | Renames break callers; run tests |
| "I already ran this earlier" | State has changed; re-run |
| "The error message is misleading" | Read it more carefully |
| "It must be flaky" | Flaky tests are real bugs; investigate |

## Checklist

- [ ] Named the command that proves the claim
- [ ] Ran the full command (not a shortened version)
- [ ] Captured actual output, not summarized
- [ ] Confirmed exit code = 0 (or expected non-zero)
- [ ] No forbidden phrases in the report
