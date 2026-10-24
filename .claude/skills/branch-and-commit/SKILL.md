---
name: branch-and-commit
description: Branch naming, commit format, opening a PR with the template filled in
---
# branch-and-commit

**Why this exists:** Consistent branches and commits keep history readable and make reverting easy
**Used by:** Reehan, Abhijit
**Triggered by:** Before any commit or PR

## When to use
Before starting work (branch), before every commit, and when opening a PR. The plain-English version of these rules is `CONTRIBUTING.md`; keep the two in agreement.

## Steps
1. **Never work on `main`.** Branch from an up-to-date `main`: `feat/<name>`, `fix/<name>`, `docs/<name>`, `spike/<name>` (kebab-case, 2-4 words, the task id helps: `feat/task-012-portfolio-chart`).
2. **Stay in the task's scope.** Check `git status`/`git diff --stat` before committing. If a file the task does not list changed, stop and ask Abhishek rather than committing it.
3. **Commit small and often**, format `<type>(<zone>): <imperative summary>` (types: feat, fix, docs, chore, refactor, test; zone: backend, frontend, spikes, docs, ci). Body only if the "why" is not obvious. No secrets, no `.env`, no stray debug code, no large data files.
4. **Before opening a PR** run `make check` and fix failures. If you changed a feature manifest, run `make readme` and commit the README table it updates (README is single-writer: use `/readme` or `make readme`, never hand-edit). Push `-u origin <branch>`.
5. **Open the PR** with `gh pr create`, filling `.github/pull_request_template.md` fully: what and why (link the `TASK-NNN`), the zone box ticked, every checklist item honestly ticked, any new dependency logged via `/decide`, feature manifest updated.
6. **Docs ship with the code.** Before each commit run the `docs-sync` skill (or `/docs-sync`). A commit with nothing to document carries `Docs-Impact: none (<specific reason>)` as the last line of its message.
7. Never force-push to a branch someone else is reviewing, and never merge your own PR; Abhishek merges.
