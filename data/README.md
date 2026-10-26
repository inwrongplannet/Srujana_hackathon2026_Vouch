# data/

**Why this exists:** small sample and seed datasets, committed so every teammate and the demo see identical data. Keep files small; no secrets or real personal data.

| Path | What it is | Used by |
|---|---|---|
| `accounts.json`, `transactions.csv` | Template sample written by `make seed` (`scripts/seed.py`): two USD accounts and 90 days of transactions, seed 42. Not read by the app. | Nothing on the demo path |
| `combined/` | Credit-assessment dataset for the ML work (see `combined/README.md`). Git-ignored: only its README is committed. | `backend/ml/` |

The demo seed lives elsewhere: the backend cast (Sahyog Microfinance anchoring Meena, Ramesh and Anand; borrowers Lakshmi, Suresh and Imran) is written to `backend/data/store.json` by `StateStore.seed_defaults` in `backend/src/veritrust/store.py`, and the guided story runs on `frontend/src/mocks/`.
