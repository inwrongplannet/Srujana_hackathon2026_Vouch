---
description: Read-only review of a PR against the team rules
---
# /review-pr

**Why this exists:** Abhishek's review time is the merge bottleneck, and a consistent checklist makes merging fast and safe
**Used by:** Abhishek

PR number or URL: $ARGUMENTS

This command is READ-ONLY. Do not edit files, commit, push or comment on the PR.

Follow the review half of the `pr-fixer` skill. Fetch the PR with `gh pr view` / `gh pr diff` / `gh pr checks`, optionally delegate the diff check to the `reviewer` subagent, and report:
- **Verdict**: merge / fix mechanical issues (`/fix-pr`) / request changes
- **Blocking issues**: secrets, float-for-money, out-of-scope edits, contract divergence, missing decision-log entry for a new dependency, failing CI
- **Mechanical issues** that `/fix-pr` could safely fix
- **Suggestions** (non-blocking)
Each finding gets `file:line` and a one-line reason.
