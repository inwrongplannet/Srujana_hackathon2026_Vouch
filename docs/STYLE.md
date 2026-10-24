# Style guide

**Why this file exists:** three people and several AI agents write docs here. One vocabulary, one structure and one set of file names keep every README and doc readable at a glance and stop agents from inventing synonyms. `make docs` enforces the machine-checkable parts.

## Principles
- Write for a skimmer with 60 seconds: the answer first, then detail.
- One fact lives in one place. Link to it; never copy it.
- Present tense, imperative mood, short sentences. No filler, no marketing, no emoji.
- Verify before you write: run the command or open the file. Delete stale text instead of leaving it.
- Docs change in the same commit or PR as the code (see `AGENTS.md`, Documentation rules).

## Canonical terms
Use these words exactly. The right-hand column is what not to write.

| Term | Meaning | Do not write |
|---|---|---|
| Abhishek, Reehan, Abhijit | The three teammates, by first name | Lead, Coder, Builder, dev A |
| zone | A top-level folder with its own `AGENTS.md` (`backend/`, `frontend/`, `spikes/`); nobody owns it | area, module, domain |
| task | One `TASK-NNN` block in `docs/TASKS.md` | ticket, story, issue |
| spike | A time-boxed experiment in `spikes/<name>/` | POC, experiment folder |
| feature manifest | One `docs/features/<name>.md` file | feature doc, feature spec |
| contract | `docs/API_CONTRACT.md` | API spec, swagger doc |
| endpoint | One method plus path in the contract | route, API call |
| skill | A how-to at `.claude/skills/<name>/SKILL.md`, readable by any agent | playbook, recipe |
| command | A slash command at `.claude/commands/<name>.md` | macro, prompt shortcut |
| subagent | A role in `.claude/agents/` | sub-agent, helper bot |
| seed data | Deterministic fake data from `make seed` | mock data, dummy data |
| demo path | The exact flow in `docs/DEMO.md` | happy flow, golden path |
| feature freeze | The point (about 70% of the time) after which only fixes land | code freeze |
| single-writer doc | README, TASKS or DECISIONS, changed only via its sanctioned route | shared doc |

Proper names: Abhishek, Reehan, Abhijit, GitHub, README, OpenCode, Claude Code, AGENTS.md, CLAUDE.md, GEMINI.md, Decimal. In prose write "pull request" (or "PR"), never "Pull Request".

## Names and files
| Where | Rule | Example |
|---|---|---|
| Repo root docs | `UPPERCASE.md` | `README.md`, `CONTRIBUTING.md` |
| `docs/*.md` | `UPPER_SNAKE.md` | `API_CONTRACT.md` |
| `docs/features/`, `docs/templates/` | `kebab-case.md` | `portfolio-view.md` |
| Skills, commands, agents | kebab-case name; skill folder equals frontmatter `name` | `.claude/skills/docs-sync/SKILL.md` |
| Spikes | `spikes/<kebab-case>/` | `spikes/fx-rates/` |
| Branches | `feat/`, `fix/`, `docs/`, `spike/` plus kebab-case | `feat/task-012-portfolio-chart` |
| Tasks, decisions | `TASK-NNN` (zero-padded), dated entries `YYYY-MM-DD` | `TASK-012` |

## Markdown rules
- First heading is the only H1 and matches the file's purpose. No skipped levels (H2 then H4).
- Headings in sentence case: "Run the demo", not "Run The Demo".
- Every fenced code block names its language (`bash`, `json`, `python`, `text`). Commands go in `bash` blocks without a leading `$`.
- Paths, commands, env vars and identifiers go in backticks. Links are relative and must resolve.
- Reference data goes in tables; steps go in numbered lists; everything else in short bullets.
- Dates are `YYYY-MM-DD`. Times are 24-hour with a timezone. Money in prose is `1,234.50 USD` (amount, then ISO 4217 code).
- `TODO` is allowed only in templates and fresh scaffolds. Elsewhere write `TODO(TASK-NNN)` so it has an owner. None may remain at the demo (`/demo-check`).
- No "last updated" lines; git records history.

## README standards
- Root `README.md`: edit only inside `<!-- BEGIN:x -->` and `<!-- END:x -->` markers (via `/readme`). Section order is fixed: overview, quickstart, features, architecture, team, demo.
- Zone READMEs (`backend/`, `frontend/`) copy `docs/templates/zone-readme.md` exactly: title equal to the folder name, a one-line description of at most 120 characters, then the H2 sections Owner, Status, Run, Structure, Interfaces, Config, Testing, Notes in that order. Section order follows the standard-readme convention: what it is, how to run it, how to use it.
- Spike READMEs copy `docs/templates/spike-readme.md` and fill every field.
- Top-level `docs/` files open with a bold "Why this file exists" line.

## Code comments and docstrings
- Comments explain why, not what. No commented-out code.
- Every new public function, class and endpoint handler has a docstring or TSDoc comment: a one-line summary, then arguments and return value only when not obvious. For money say the currency, units and rounding rule.
