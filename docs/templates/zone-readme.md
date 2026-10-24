<!-- Why: every zone README has the same sections in the same order, so a human or an agent finds how to run, test and configure a zone instantly. Copy to <zone>/README.md and keep the H2 headings exactly. -->
# <zone>
One-line description of what this zone does (at most 120 characters).

## Status
What works today, what is in progress, what is missing.

## Run
Exact commands from a fresh clone (install, then `make dev`). Verified, not guessed.

## Structure
Folder layout and where new code goes, one line per folder.

## Interfaces
Endpoints (link to `docs/API_CONTRACT.md`), CLI commands, or exported modules other zones use.

## Config
Environment variables used here (also listed in `.env.example`) and any settings files.

## Testing
How to run all tests and a single test, and what the tests cover.

## Notes
Gotchas, decisions (link to `docs/DECISIONS.md`) and known limits.
