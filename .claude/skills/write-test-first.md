---
name: write-test-first
description: TDD red→green→refactor procedure. Use BEFORE writing any implementation code.
---

# Write the Test First

**This skill is the spine of the project.** If you skip it, the PreCommit hook will reject the commit anyway.

## Procedure

1. **Identify the smallest piece of behavior you can verify.**
   - Bad: "implement the stress engine".
   - Good: "compute portfolio EL under a 20% house-price shock equals the hand-calculated value within 0.1%".

2. **Write the failing test.** Put it in `tests/unit/<area>/test_<module>.py`. Match the directory layout under `src/`.
   ```python
   def test_dnb_house_price_shock_20pct():
       tape = load_golden_tape()
       stressed = apply_house_price_shock(tape, shock=-0.20)
       el_delta = portfolio_el(stressed) - portfolio_el(tape)
       assert el_delta == pytest.approx(1_250_000.0, rel=0.001)
   ```

3. **Run it. See it fail.**
   ```bash
   uv run pytest tests/unit/analytics/test_stress.py::test_dnb_house_price_shock_20pct -x
   ```
   Failure must be a real failure (import error, NameError, AssertionError). If the test passes against no implementation, the test is wrong.

4. **Write the minimum implementation to make it pass.** Do not add features the test does not exercise.

5. **Run the test. See it pass.** Iron Law: read the actual output.

6. **Refactor.** Extract helpers, rename, tidy. Run the test after each refactor.

7. **Commit.** Single focused commit with `[ai-assisted]` trailer.

## Anti-patterns the hook will catch

| Anti-pattern | What happens |
|---|---|
| Implementation added without matching test file | `precommit_tdd_guard.py` blocks commit |
| Test added *after* implementation in same commit | Allowed for ergonomic reasons, BUT next code change requires test-first again |
| Commit > 500 lines without re-affirmation | `precommit_mass_rewrite_guard.py` blocks commit |
| AI-authored commit missing `[ai-assisted]` trailer | `precommit_ai_trailer.py` blocks commit |

## Checklist

- [ ] Test file exists in `tests/unit/` matching `src/` path
- [ ] Test fails for the *right reason* before implementation
- [ ] Implementation is minimal (does not add untested behavior)
- [ ] Test passes after implementation
- [ ] Ran `pytest -x` and read the exit code
- [ ] Commit includes `[ai-assisted]` trailer
