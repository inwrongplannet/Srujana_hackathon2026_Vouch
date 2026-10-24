---
name: feature-manifest
description: Create and update docs/features/<name>.md manifests and keep the README features table in sync
---
# feature-manifest

**Why this exists:** Manifests are the one source for the README features table, `/status` and the demo checklist; if they are stale, all three lie
**Used by:** Everyone
**Triggered by:** Starting, finishing or renaming a feature

## When to use
A feature starts, changes status, or is cut.

## Steps
1. Copy `docs/templates/feature-manifest.md` to `docs/features/<kebab-name>.md`. Heading must be `# Feature: <Display Name>`.
2. Fill the fields exactly in this form (the parser in `scripts/update_readme.py` reads these lines):
   - `- **Assignee:**` Abhishek, Reehan or Abhijit
   - `- **Status:**` one of `planned`, `in-progress`, `done` (use `cut` only if the team agrees to drop it, and say why in `docs/DECISIONS.md`)
   - `- **One-liner:**` what the user can do, in under ~15 words, no jargon
3. Update the Status in the same PR that changes the feature's state: `in-progress` when the first PR opens, `done` when it merges and works on the demo path with seed data.
4. Run `make readme` to regenerate the README table (never hand-edit the README table). `make check` fails when the table is out of date.
5. Never put implementation notes, TODO lists or long text in manifests; those belong in `docs/TASKS.md` or the PR.
