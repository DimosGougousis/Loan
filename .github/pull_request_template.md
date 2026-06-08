# Pull Request

## Summary

<!-- One paragraph: what changed and why. -->

## Type of change

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Documentation
- [ ] Harness (`.claude/`, CI, hooks)

## Regulatory anchors touched

<!-- Cite every regulation this PR's quantitative rules rely on. Example: "IFRS 9 par. 5.5.11", "EBA GL/2017/06", "DNB climate guidance 2024", "NHG / WEW", "Tijdelijke regeling hypothecair krediet". -->

## Governance checklist

- [ ] Tests added/updated and green locally (`uv run pytest`)
- [ ] Eval rubrics updated (regulated paths only)
- [ ] `docs/governance/model-inventory.md` updated (if new quantitative rule)
- [ ] `docs/regulation-map.md` updated (if new regulation cited)
- [ ] All AI-authored commits carry `[ai-assisted]` trailer
- [ ] No single commit > 500 changed lines
- [ ] `/governance-check` passes

## 2nd-line review required?

<!-- Required if touching: src/loan_tape/ecl/, src/loan_tape/analytics/stress.py, src/loan_tape/validate/rules.py, evals/rubrics/ -->

- [ ] Not applicable
- [ ] Required — `2nd-line-approved` label set before merge

## EU AI Act articles touched

<!-- Tick all that apply -->

- [ ] Art. 9 (risk management) — eval rubric or fail-gracefully behavior added/changed
- [ ] Art. 10 (data governance) — schema or generator change
- [ ] Art. 13 (transparency) — UI About/Limits panel updated
- [ ] Art. 14 (human oversight) — approval gate or sign-off change
- [ ] Art. 15 (accuracy / robustness / cybersecurity) — test, lint, or secrets-scan change

## Fail-gracefully behaviors added

<!-- New named failure modes in src/loan_tape — list each one and its contracted behavior. Cross-reference docs/governance/fail-gracefully.md. -->

## Verification evidence

<!-- Paste the output of `uv run pytest -q` and `uv run python evals/runner.py`. The Iron Law: do not claim "tests pass" without the receipt. -->

```
<paste here>
```

## Screenshots (UI changes only)

<!-- Embed screenshots of the affected Streamlit pages. -->
