---
name: status-report
description: Summarize git log, PRs, TASKS.md and docs/features statuses
---
# status-report

**Why this exists:** Gives Abhishek one view of progress and blockers without pinging teammates
**Used by:** Abhishek
**Triggered by:** `/status`

## When to use
Abhishek wants a snapshot of progress. Read-only: never modify files or state.

## Steps
1. Gather: `git log --since="12 hours ago" --oneline --all` (adjust window to the event), `gh pr list --state open --json number,title,author,isDraft,reviewDecision,statusCheckRollup`, `docs/TASKS.md` (Backlog / In progress / Done), `docs/features/*.md` statuses.
   Optionally run `make check` on `main` (or the PR branch) to include current gate status.
2. Report in this order, tersely:
   - **Headline**: percent of tasks done, time used vs remaining if known, and whether the feature-freeze (~70%) is on track.
   - **Per person** (Abhishek, Reehan, Abhijit): done recently, in progress, next.
   - **Open PRs**: number, author, CI state, age, what they are waiting on.
   - **Blockers and risks**: failing CI, stale PRs, tasks In progress with no commits, contract gaps, missing demo pieces (seed data, DEMO.md script).
   - **Features**: planned / in-progress / done table.
3. End with the 1-3 highest-value next actions for Abhishek. Do not pad; unknowns are stated as unknown.
