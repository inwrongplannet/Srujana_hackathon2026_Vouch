---
name: docs-sync
description: After any code or config change, find and update every doc it affects (zone README, contract, feature manifest, env example, AGENTS.md), then run the docs gates
---
# docs-sync

**Why this exists:** docs rot the moment code moves without them, and stale docs mislead both teammates and agents. This is the one procedure that keeps docs true after every change, even a one-line change.
**Used by:** Everyone, every PR
**Triggered by:** `/docs-sync`, `/finish`, and any time you changed a file

## When to use
Before every commit that changes code, config, scripts, skills or structure. Also when the Stop hook, `make docs`, the pre-push hook or CI reports `docs-sync FAILED`.

## Steps
1. **List what changed.** Run `git diff --name-status $(git merge-base origin/main HEAD)` and `git ls-files -o --exclude-standard` (untracked). If there is no `origin/main`, use `git status`.
2. **Map each change to docs** with the table in `AGENTS.md` (Documentation rules). Typical targets: zone README (Run, Structure, Interfaces, Config, Testing), `docs/API_CONTRACT.md`, `docs/frontend-features/<name>.md`, `.env.example`, `docs/DECISIONS.md`, `docs/DEMO.md`, `data/README.md`, `docs/REPO_GUIDE.md`.
3. **Verify, then write.** Open each target doc. Run the command or read the code to confirm the facts; never document from memory. Make the smallest accurate edit and delete text that is now false.
4. **Comments and docstrings.** Every new public function, class and endpoint handler has a docstring (summary; arguments and return when not obvious; currency, units and rounding for money).
5. **AGENTS.md sync (mandatory when conventions moved).** Did a command, convention, structure, tool, skill or rule change? Update `AGENTS.md` (or the zone's `AGENTS.md` for zone-specific rules). Stay inside the line budgets (root 150, zone 80): prune before you add. Never put rules in `CLAUDE.md` or `GEMINI.md`. Update the Skills and commands table and the OpenCode wrapper when you add a skill, command or agent. If a human corrected you, add one dated line under Lessons.
6. **Nomenclature pass.** Check changed docs against `docs/STYLE.md`: canonical terms, heading levels, fenced code languages, relative links, file names. README sections follow `docs/templates/zone-readme.md`.
7. **Run the gates.** `make readme` if a feature manifest changed, then `make docs`. Fix every message it prints.
8. **Waiver (rare).** Only for a typo, comment-only change, test-only change, pure refactor with unchanged behaviour, or formatting: put `Docs-Impact: none (<reason>)` (and/or `Agents-Impact: none (<reason>)`) in the commit message. The reason must be specific. Never use it to skip real documentation.
9. **Report** a short list: change -> doc updated (or waiver and why).
