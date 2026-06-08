# RACI — Activity Ownership

> R = Responsible · A = Accountable · C = Consulted · I = Informed

## Activity-level RACI

| Activity | 1st line | 2nd line | 3rd line | IT |
|---|:-:|:-:|:-:|:-:|
| Define use case / requirement | **R/A** | C | I | I |
| Build feature with Claude | **R/A** | C | I | I |
| Write failing test | **R/A** | I | — | — |
| Implement code (AI-assisted) | **R/A** | I | — | — |
| Define stress scenario | **R** | **A** | I | — |
| Approve eval thresholds | C | **R/A** | I | — |
| Approve new SICR trigger | C | **R/A** | I | — |
| Approve new validation rule | C | **R/A** | I | — |
| Code review on PR | **R** | C (regulated paths) | — | — |
| Merge to `main` | **R/A** | C | — | I |
| Tag release (SemVer) | **R/A** | C | I | I |
| Deploy to production | C | **A** | I | **R** |
| Run pipeline on real tape | **R/A** | I | — | — |
| Sign off published report | C | **R/A** | I | — |
| Periodic audit | I | C | **R/A** | I |
| Incident response | **R** | C | I | C |
| Update model inventory | **R** | **A** | I | — |
| Update fail-gracefully playbook | **R** | **A** | I | — |
| EU AI Act conformance review | I | **R/A** | C | I |

## Notes

- "1st line" = Credit Risk Portfolio Analytics team (the team using this platform).
- "2nd line" = Model Risk Management + Compliance.
- "3rd line" = Internal Audit.
- "IT" = Bank IT (security, infrastructure, deployment).
- Where 1st and 2nd line share R/A — 1st implements, 2nd approves.
