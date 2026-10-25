@AGENTS.md

# Claude Code specifics

Shared rules are imported above from `AGENTS.md`. Edit them there, never here.

- A Stop hook (`.claude/settings.json`) runs `scripts/check_docs.py` and blocks you from finishing while code changed without its docs. Update the docs or state a `Docs-Impact: none (<reason>)` waiver; it only blocks once per turn.
- Use `/start`, `/finish` and `/docs-sync` to run the session protocol. Plan mode for multi-file changes; skip it when the diff fits in one sentence.
- Run `/clear` between unrelated tasks, and after two failed corrections. Send research to the `researcher` subagent and let the `reviewer` subagent check your diff in a clean context.
- `.claude/settings.json` pre-approves `make` and read-only git and gh commands and blocks reading `.env*`. Do not widen it without Abhishek.
- Never auto-merge PRs or push directly to main. Push your branch and open a PR for Abhishek's review.
