@AGENTS.md

# Gemini CLI specifics

All project rules are in `AGENTS.md` (imported above); `.gemini/settings.json` also makes Gemini CLI read `AGENTS.md` at every level. Edit shared rules there, not here. Skills and commands under `.claude/` are plain markdown: open the matching file from the table in `AGENTS.md` and follow it.

- Never auto-merge PRs or push directly to main. Push your feature branch and open a PR for Abhishek's review.
