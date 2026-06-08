# Change Management — Approval Gates and SemVer

## Approval gates

Every PR passes a gate before merging:

| Gate | Required | Enforced by |
|---|---|---|
| CI green | ruff + pytest + evals + secrets scan | GitHub Actions |
| TDD compliance | every src/ change has a paired tests/ change | `precommit_tdd_guard.py` |
| AI-authorship trailer | `[ai-assisted]` on every AI-authored commit | `precommit_ai_trailer.py` |
| Mass-rewrite guard | no single AI commit > 500 changed lines | `precommit_mass_rewrite_guard.py` |
| Secrets scan | `detect-secrets` clean | `precommit_secrets.py` + CI |
| 1st-line peer review | 1 approval on PR | GitHub branch protection |
| 2nd-line review (regulated paths) | `2nd-line-approved` label | `/governance-check` + GitHub branch protection |
| Model inventory updated | every new quantitative rule appears in `model-inventory.md` | reviewer + `/governance-check` |
| Regulation map updated | every new regulatory citation appears in `regulation-map.md` | reviewer + `/governance-check` |
| Eval rubric updated | every change to a regulated path updates the corresponding rubric | `/governance-check` |

## Regulated paths

Paths requiring 2nd-line review:

- `src/loan_tape/ecl/**`
- `src/loan_tape/analytics/stress.py`
- `src/loan_tape/validate/rules.py`
- `evals/rubrics/**`
- `data/reference/**` (any change to NHG caps, HRA rates, Nibud LTI)

## Versioning (SemVer)

- **MAJOR** — schema breaking change; any field rename or removal; any AnaCredit attribute mapping change.
- **MINOR** — new field, new rule, new scenario, new SICR trigger, new dashboard tab.
- **PATCH** — bug fix, doc-only change, refactor with no behavior change.

Tag releases on `main` after a merged PR. Release notes link the eval-result file and the 2nd-line sign-off comment (if applicable).

## Quarterly eval review

Every 90 days, 2nd line reviews:

1. Eval-result history under `evals/results/` for drift.
2. Model inventory for stale entries (`last_reviewed_date` > 6mo).
3. Decisions log for patterns (recurring overrides → policy change candidate).

Outcome: updated rubrics, retired rules, model-inventory refresh.

## Emergency change (incident)

If production is failing (e.g., reporting wrong figures to the business):

1. 1st line opens incident in `incidents/` via the platform's structured incident logger.
2. Hotfix branch off `main` → minimal change → `[ai-assisted]` commit if AI used → tests added even if just one regression case.
3. 2nd-line approval required even on hotfix path for regulated changes (verbal approval acceptable; document in `decisions.md` post-incident).
4. Post-incident review within 5 business days. Update `fail-gracefully.md` if a new failure mode was discovered.
