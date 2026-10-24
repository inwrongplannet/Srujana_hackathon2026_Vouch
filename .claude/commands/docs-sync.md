---
description: Audit the current changes and update every doc they affect, then run the docs gates
---
# /docs-sync

**Why this exists:** docs must change with the code, even for a one-line change; this finds and fixes the gaps on demand.
**Used by:** Everyone, after any change

Focus (optional): $ARGUMENTS

Follow the `docs-sync` skill: list the changes, map each to its docs with the table in `AGENTS.md`, verify and update them, sync `AGENTS.md` if a convention moved, check `docs/STYLE.md`, then run `make docs` (and `make readme` if a feature manifest changed). Do not commit. Finish with the change -> doc list.
