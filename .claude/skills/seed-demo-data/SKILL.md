---
name: seed-demo-data
description: Generate deterministic, realistic fake finance data for reproducible demos
---
# seed-demo-data

**Why this exists:** The demo must not depend on live APIs or luck
**Used by:** Abhishek, Reehan
**Triggered by:** Building or resetting demo data

## When to use
Creating or changing demo data, or when the demo looks different between runs.

## Steps
1. **Determinism**: the generator is `scripts/seed.py`, run through `make seed`. It already has `SEED`, `AS_OF`, `DAYS`, `CURRENCY`, `ACCOUNTS` and `CATEGORIES` constants and writes `data/accounts.json` and `data/transactions.csv`. Extend those instead of rewriting it. Keep one fixed seed, a fixed `AS_OF` date (never `date.today()`), sorted output and `\n` newlines, so two runs produce byte-identical files. Never call live APIs from the seed.
2. **Realism**: finance-plausible values with the right shapes: log-normal-ish transaction amounts, salary-like monthly inflows, month-end bills, weekday-heavy spending, prices as random walks with small drift, realistic currency, categories and merchants. Money is `Decimal` quantized to the currency's minor unit; never float.
3. **Tell the story**: build the demo narrative from `docs/DEMO.md` into the data: at least one clear insight to show (an overspending category, a covenant breach, a drawdown event), plus edge cases (zero balance, refund/negative amount, dormant account, missing field, same-day duplicates).
4. **Safety**: entirely synthetic. Fake names, no real PII, no real account or card numbers (use obviously fake or Luhn-invalid ones), no real company data presented as real. Keep files small; commit outputs under `data/` and mention the schema in `data/README.md`.
5. **Contract**: shape output to match `docs/API_CONTRACT.md` so the frontend can run on it unchanged.
6. **Verify**: run `make seed` twice and compare hashes of everything in `data/`; the output must be identical. Commit the regenerated `data/` files in the same PR as the generator change. Run `make check`. Document any new schema or field and update the feature manifest if a feature depends on it.

## Project-specific seed schema (replaces generic accounts/transactions)

This project seeds a **trust graph**, not a bank ledger. Target output files in `data/`:

### `data/nodes.json`
```json
[{
  "id": "node_001",
  "nullifier_stub": "<sha256 hex>",
  "status": "ACTIVE",
  "R_score": "42.50",
  "sigma2": "0.18",
  "N_settled": 3,
  "cash_flow_score": "0.72",
  "cluster": "urban_msme",
  "label": "Mid-tier voucher"
}]
```

### `data/edges.json`
```json
[{ "from_id": "anchor_001", "to_id": "node_001", "weight": "10.00", "locked": false }]
```

### `data/loans.json`
```json
[{
  "id": "loan_001",
  "borrower_id": "node_005",
  "principal_minor_units": 1000000,
  "currency": "INR",
  "status": "SETTLED",
  "repayment_events": [{"date": "2025-02-01", "amount_minor_units": 500000}]
}]
```

### `data/cashflow.json`
```json
{
  "node_005": [
    { "month": "2025-01", "income_minor_units": 3000000, "obligations_minor_units": 800000, "currency": "INR", "completeness": 0.9 }
  ]
}
```

### Demo narrative (build this into the seed)
- **2-3 institutional anchors**: `R >= 100`, `sigma2 < 0.05`, `cluster: anchor`
- **5-8 mid-tier vouchers**: `R 30-80`, multiple settled loans, active outgoing vouches
- **10-15 thin-file borrowers**: `R = 0`, `sigma2 = 1.0`, one incoming vouch, no cash-flow history
- **1 DEFAULTED node**: cascade partially applied to its k=1 and k=2 sponsors (demonstrate slashing)
- **1 RESTRICTED node**: R dropped below 0 from a k=1 penalty, no primary default
- **1 cold-start isolated node**: `R = 0`, no vouches, `sigma2 = 1.0` — shows graceful handling

Fixed constants: `SEED=42`, `AS_OF="2025-01-01"`. Never call live APIs. Output must be byte-identical across runs. All monetary amounts are integer minor units (paise for INR). R_score and sigma2 are decimal strings.
