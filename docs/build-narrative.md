# Build Narrative — How Claude Wrote This

> The interview gold. Three (or more) concrete moments where Claude was prompted to build something, where the test caught a regression or the eval surfaced a drift, and how the harness corrected it. Filled in during Days 1–3 of the build.

## The framing

This repo was built end-to-end with Claude Code as a portfolio piece. Claude wrote ~70% of the code. The interesting question is not "did AI write it" — it's *"what kept the AI-written code correct and defensible to a 2nd-line reviewer?"* This document answers that with three illustrative moments.

The harness is the answer:

- A `CLAUDE.md` pinning the Dutch mortgage schema.
- Seven skills under `.claude/skills/` encoding TDD, validation, stress, SICR, anomaly procedures.
- Hooks that ran ruff and pytest on every edit, tagged AI commits, blocked TDD violations and mass rewrites.
- An eval suite with rubrics that caught drift before merge.
- A Three Lines of Defense governance model and an EU AI Act position.

## Cycle 1 — [placeholder; filled during Day 1–2 build]

**Prompt:**
> [the original prompt issued to Claude]

**Diff (excerpt):**
```python
# Claude's first attempt
```

**The test / eval that caught it:**
```
$ uv run pytest tests/unit/...
FAILED ... because ...
```

**What was learned / corrected:**
[short paragraph]

## Cycle 2 — [placeholder]

[same structure]

## Cycle 3 — [placeholder]

[same structure]

## Candidate moments to capture (Day 1–2 build hints)

These are good candidates for the three cycles above — pick the ones with the cleanest story:

- **SICR climate-transition trigger** — getting the `energy_label IN {E, F, G}` condition wrong on first attempt (e.g., off-by-one or missed the bouwjaar conjunction). Caught by the negative fixture.
- **HRA phase-out scenario** — off-by-one on the post-2013 cutoff (whether 2013-01-01 is inclusive or exclusive). Caught by the eval rubric.
- **Fail-gracefully on NaN in Quick Scan** — Claude initially returned 0.0 silently when a portfolio aggregate divided by zero. Eval caught it; fix surfaces `FAILED` per the playbook.
- **NHG cap rule** — Claude used a constant instead of year-of-origination lookup. Caught by the easter-egg fixture.
- **AnaCredit mapper** — Claude initially mapped `tax_deduction_eligible` to the wrong AnaCredit attribute. Caught by the conformance check.
- **Stress engine sign error** — Claude implemented house-price shock with `(1 - shock)` instead of `(1 + shock)`, producing a positive value-add under a downside scenario. Caught by the eval rubric's sanity-band assertion.

## Verification

Each cycle above includes the exact pytest output (Iron Law). No "the test should pass" without showing it.

## See also

- `.claude/skills/` — the build patterns referenced in each cycle
- `evals/results/` — the eval history that gated each cycle
- `docs/governance/decisions.md` — any 2nd-line equivalent decisions during the build
