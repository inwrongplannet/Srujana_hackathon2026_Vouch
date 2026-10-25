---
name: readme-editor
description: The only sanctioned way to edit README.md, inside BEGIN/END markers only
---
# readme-editor

**Why this exists:** Three people editing one README causes conflicts and drift, and judges read it first
**Used by:** Everyone
**Triggered by:** `/readme`

## When to use
Any change to README.md.

## Steps
1. Read README.md. The editable regions are the pairs `<!-- BEGIN:name -->` ... `<!-- END:name -->` (overview, quickstart, features, architecture, team, demo). Everything outside the markers (title, footer link) is frozen except the project title at kickoff.
2. Decide which section the request belongs in. Edit only inside that pair; never add, remove, rename or move markers.
3. Section rules:
   - **overview**: one or two sentences: the pain, the user, how we help. Source: `docs/PROBLEM.md`.
   - **quickstart**: exact commands that work from a fresh clone; verify every command against the Makefile and `.env.example`. No unverified instructions.
   - **features**: generated from `docs/frontend-features/*.md`. Run `make readme` (wraps `scripts/update_readme.py`); do not hand-type the table.
   - **architecture**: short paragraph, diagram and link to `docs/ARCHITECTURE.md`.
   - **team**: names and roles. **demo**: link and a 3-line summary of the script in `docs/DEMO.md`.
4. Write for a judge skimming for 60 seconds: concrete, no filler, no `TODO` left in sections that are ready.
5. Run `make check`. It runs `scripts/check_structure.py` (all six marker pairs present once, in order, and text outside them unchanged versus `origin/main`) and `update_readme.py --check` (features table up to date). Fix whatever it reports, then show the diff to the user.
6. If the check says text outside the markers changed, revert that part with `git diff README.md`; do not edit the check or the markers to make it pass.
