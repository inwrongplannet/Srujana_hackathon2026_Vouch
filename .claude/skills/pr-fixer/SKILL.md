---
name: pr-fixer
description: Review a teammate's PR against team rules, then fix mechanical issues on their branch
---
# pr-fixer

**Why this exists:** With a 24-48h clock and three people, hand-reviewing every PR is slow and inconsistent, and trivial fixes waste round trips
**Used by:** Abhishek
**Triggered by:** `/review-pr`, `/fix-pr`

## When to use
Reviewing (`/review-pr`, read-only) or fixing (`/fix-pr`) a teammate's pull request.

## Review steps (read-only)
1. `gh pr view <n> --json title,body,author,headRefName,files` and `gh pr diff <n>`; `gh pr checks <n>` for CI.
2. Compare the changed files with the linked task's Files touched in `docs/TASKS.md` and flag every file it does not list.
3. Check against the PR checklist, `CONTRIBUTING.md` and `AGENTS.md` (CI runs `make check`, including `scripts/check_structure.py`, so a red check often names the exact problem): `make check` green, no secrets or debug code, no float money, contract matches `docs/API_CONTRACT.md`, new dependency has a `docs/DECISIONS.md` entry, feature manifest updated, single-writer docs untouched by hand.
4. For a large diff, hand it to the `reviewer` subagent to keep this context clean.
5. Classify every finding as **Blocking**, **Mechanical** (safe to auto-fix) or **Suggestion**, each with `file:line`. Give a verdict: merge, fix mechanical, or request changes.

## Fix steps (`/fix-pr`)
1. Check out the PR branch with a clean tree. If the branch is from a fork or you cannot push, report instead of fixing.
2. Fix only mechanical issues: formatting, lint autofix, regenerate generated files (`make types` for API types, `make readme` for the README features table, `make seed` if only the generator output is stale), `.env.example` entries, PR template gaps. Never change behavior, logic, tests, or the contract.
3. Run `make check`. Commit as a NEW commit `chore(<zone>): mechanical fixes from review` with no amend and no force-push. Push.
4. Report what was fixed and every non-mechanical issue left for the author or Abhishek. Never merge.

## Docs
Missing docs is a Blocking finding, not a mechanical fix: name the doc from the map in `AGENTS.md` and ask the author to update it. Only regenerated docs (`make readme`) are mechanical.

## Guardrails
Do not rewrite someone's approach, rename things for taste, or "improve" code. When unsure whether a fix is mechanical, it is not: leave it as a comment.
