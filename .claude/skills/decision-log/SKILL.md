---
name: decision-log
description: Append dated entries to docs/DECISIONS.md, required for new dependencies
---
# decision-log

**Why this exists:** Keeps a trail of why we chose things, stops repeat debates, feeds the pitch
**Used by:** Everyone
**Triggered by:** `/decide`

## When to use
Choosing a stack, library, API, data source, or approach that others would otherwise re-debate; and always when adding a dependency.

## Steps
1. Read `docs/DECISIONS.md` to avoid duplicates; if an earlier decision is being reversed, reference it.
2. Add one entry immediately below `<!-- ENTRIES -->` (newest first) in this format:

```text
### YYYY-MM-DD: <short title>
- **Decision:** what we chose
- **Why:** the reason, tied to the PS, judging criteria or time
- **Alternatives considered:** each with the reason rejected
- **Consequences:** what this commits us to or makes harder
- **By:** <name>
```
3. For a new dependency also record the exact package and version, licence, and whether it needs a network or key at demo time.
4. Keep it short (under ~8 lines). Use today's real date, never invent one. Do not edit older entries except to add a "Superseded by" note.
