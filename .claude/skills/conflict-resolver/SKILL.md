---
name: conflict-resolver
description: Resolve merge conflicts with main as the tiebreaker, then run `make check`
---
# conflict-resolver

**Why this exists:** Conflicts will happen late at night, and a fixed rule (main wins, you re-apply your change) avoids arguments and mistakes
**Used by:** Abhishek
**Triggered by:** On merge conflict

## When to use
A merge or rebase reports conflicts.

## Steps
1. `git status` and `git diff --name-only --diff-filter=U` to list conflicted files. Never use `--ours`/`--theirs` blanket resolution without reading each file.
2. Decide per file:
   - Ordinary code: **the version already on main wins** for contested lines (it was reviewed); re-apply your change on top of it, keeping both sides when they are additive and compatible.
   - Single-writer docs (`README.md`, `docs/TASKS.md`, `docs/DECISIONS.md`): keep **both** sides' content (union), preserving markers, ids and newest-first order; renumber a duplicate `TASK-NNN` to the next free id. For README, never keep conflict markers inside marker sections, and run `make readme` afterward so the features table is regenerated rather than hand-merged.
   - Seed output in `data/`: do not hand-merge; resolve `scripts/seed.py` first, then run `make seed` and add the result.
   - Generated files (types, lockfiles): do not hand-merge; take either side, then regenerate (`make types`, package manager install).
   - `docs/API_CONTRACT.md`: main's version wins; flag the affected endpoint to the other author and Abhishek.
3. Remove all conflict markers (`grep -rn '<<<<<<<\|>>>>>>>' .` must be empty), then `git add` and continue the merge/rebase.
4. Run `make check` (`scripts/check_structure.py` also flags leftover conflict markers and broken README markers). If it fails, fix only what the merge broke.
5. Summarize each file: what was kept, from whom, and why, so the authors can verify. If a conflict is a real logic disagreement (not formatting or additive), stop and ask Abhishek instead of choosing.
