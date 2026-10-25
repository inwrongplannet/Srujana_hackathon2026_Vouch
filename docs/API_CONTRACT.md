# API Contract

**Why this file exists:** Abhishek writes endpoint shapes here *before* anyone implements them, so frontend and backend can be built in parallel without waiting on each other.

## Overview
All endpoints accept and return `application/json`. Timestamps follow ISO 8601 UTC. Money is a decimal string in INR (rupees, two decimal places where the engine rounds). Scores, weights and reputations are decimal strings; probabilities and percentages are JSON numbers. Every endpoint declares its response model, so `make types` generates `frontend/src/types/api.d.ts` from `GET /openapi.json`. Errors use `{"detail": "<message>"}` (FastAPI's list form for validation errors). IDs in the examples are the demo seed (`backend/data/store.json`): Sahyog Microfinance anchors Meena, Ramesh and Anand; Lakshmi, Suresh and Imran borrow. All figures are illustrative.

---

## 1. Application endpoints

### Create loan application
- **Method + path:** `POST /api/v1/applications`
- **Request:**
  ```json
  {
    "borrower_id": "LAKSHMI",
    "principal": "150000",
    "annual_rate": 0.24,
    "term_months": 24,
    "purpose_category": "WORKING_CAPITAL"
  }
  ```
- **Response:**
  ```json
  {
    "application_id": "APP_B9DBFFCA",
    "borrower_id": "LAKSHMI",
    "principal": "150000",
    "term_months": 24,
    "status": "SUBMITTED",
    "created_at": "2026-10-25T06:40:32Z"
  }
  ```
- **Status:** 201 Created; 404 if the borrower does not exist. Applications live in memory until the server restarts.

### Register application evidence
- **Method + path:** `POST /api/v1/applications/{id}/evidence`
- **Request:**
  ```json
  {
    "evidence_type": "BANK_STATEMENT",
    "source": "ACCOUNT_AGGREGATOR",
    "uri_or_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "confidence": 0.95,
    "description": "Verified 6-month bank statement via DigiLocker"
  }
  ```
- **Response:**
  ```json
  {
    "evidence_id": "EVID_20261025_001",
    "application_id": "APP_B9DBFFCA",
    "status": "REGISTERED",
    "verified_at": "2026-10-25T07:30:00Z"
  }
  ```
- **Status:** 201 Created

### Decide an application
- **Method + path:** `POST /api/v1/applications/{id}/decision`
- **Request:** `{"decision": "APPROVE"}`. `APPROVE` lends the amount asked; `APPROVE_AT_LIMIT` lends the smaller of that and the borrower's current limit; `DECLINE` rejects.
- **Response:**
  ```json
  {
    "application_id": "APP_B9DBFFCA",
    "status": "APPROVED",
    "loan": {
      "loan_id": "LN_00001",
      "borrower_id": "LAKSHMI",
      "principal": "150000",
      "outstanding_balance": "150000",
      "interest_rate": "0.24",
      "tenure_months": 24,
      "status": "ACTIVE"
    }
  }
  ```
  `loan` is `null` on `DECLINE` (status `REJECTED`).
- **Status:** 200 OK; 400 if the amount is over the borrower's limit or the limit is 0; 404 unknown application; 409 already decided.

---

## 2. Endorsement endpoints

### Issue peer endorsement
- **Method + path:** `POST /api/v1/endorsements`
- **Request:**
  ```json
  {
    "endorser_id": "MEENA",
    "recipient_id": "IMRAN",
    "statement": "Imran has run the stall beside my shop for two years"
  }
  ```
- **Response:**
  ```json
  {
    "endorsement_id": "V_MEENA_IMRAN",
    "endorser_id": "MEENA",
    "recipient_id": "IMRAN",
    "allocated_weight": "5.0",
    "status": "ACTIVE",
    "created_at": "2026-10-25T07:30:00Z"
  }
  ```
- **Status:** 201 Created; 400 on self-vouching, zero capacity or a duplicate.

### Ask for a vouch
- **Method + path:** `POST /api/v1/vouch-requests`
- **Request:** `{"requester_id": "LAKSHMI", "voucher_id": "MEENA", "note": "Neighbour of 9 years"}`
- **Response:**
  ```json
  {
    "request_id": "VREQ_8DF1DCF8",
    "requester_id": "LAKSHMI",
    "voucher_id": "MEENA",
    "note": "Neighbour of 9 years",
    "status": "PENDING",
    "endorsement_id": null,
    "created_at": "2026-10-25T06:40:32Z"
  }
  ```
- **Status:** 201 Created; 400 self; 404 unknown user; 409 already vouching or already pending. Requests live in memory until the server restarts.

### List vouch requests
- **Method + path:** `GET /api/v1/vouch-requests?voucher_id=MEENA&requester_id=LAKSHMI&status=PENDING` (all filters optional)
- **Response:** a list of vouch requests as above.
- **Status:** 200 OK

### Answer a vouch request
- **Method + path:** `POST /api/v1/vouch-requests/{id}/respond`
- **Request:** `{"accept": true}`
- **Response:** the request with `status` `ACCEPTED` (and `endorsement_id`, e.g. `V_MEENA_LAKSHMI`, created with conserved weights) or `DECLINED`.
- **Status:** 200 OK; 400 if the endorsement cannot be created; 404 unknown request; 409 already answered.

### Get user vouch summary
- **Method + path:** `GET /api/v1/users/{id}/vouch-summary`
- **Response:**
  ```json
  {
    "user_id": "LAKSHMI",
    "vouch_score": "63.5",
    "confidence_rating": "MEDIUM",
    "eligible_endorsement_count": 2,
    "reputation_capacity": "0.0",
    "active_incoming_paths": 2
  }
  ```
  `vouch_score` is 0-100 with tau = 3, the Vouch scoring proposal's value.
- **Status:** 200 OK; 404 unknown user.

---

## 3. Assessment and optimization endpoints

### Run credit assessment & optimization
- **Method + path:** `POST /api/v1/applications/{id}/assessments`
- **Request:**
  ```json
  {
    "objective": "MIN_COST",
    "enable_stress_test": true,
    "simulation_scenarios": 5000,
    "bureau_status": "NO_FILE",
    "bureau_score": null
  }
  ```
- **Response** (Lakshmi asking for 1,50,000 INR over 12 months at 24%, from a live run):
  ```json
  {
    "assessment_id": "ASM_4AC19E0AFA3D",
    "application_id": "APP_B9DBFFCA",
    "borrower_id": "LAKSHMI",
    "verdict": "RESTRUCTURED_ALTERNATIVE",
    "bureau_status": "NO_FILE",
    "bureau_score": null,
    "vouch_score": "63.5",
    "affordability": {
      "gross_monthly_income": "38000.00",
      "non_discretionary_outflows": "22500.00",
      "disposable_income": "8945.00",
      "max_affordable_emi": "8945.00",
      "protected_cash_buffer": "6555.00",
      "status": "SUFFICIENT",
      "binding_rule": "DISPOSABLE_INCOME"
    },
    "best_plan": {
      "principal": "150000.00",
      "term_months": 24,
      "monthly_emi": "7930.66",
      "total_interest": "40335.84"
    },
    "stress_resilience": {
      "rating": "MODERATE",
      "shortfall_probability": 0.131,
      "adverse_5th_percentile_cash": "-4710.64",
      "income_shock_tolerance_percent": 19.92
    },
    "reason_codes": ["INCOME_PRESENT", "INCOME_STABLE", "COMMUNITY_VOUCH_ACTIVE", "DISPOSABLE_INCOME_SUFFICIENT", "AFFORDABILITY_DEFICIT", "STRESS_TEST_MODERATE"],
    "positive_factors": [{"code": "INCOME_PRESENT", "text": "Verified recurring monthly income of INR 38,000.00 documented", "source": "BANK_STATEMENT"}],
    "risk_factors": [{"code": "AFFORDABILITY_DEFICIT", "text": "Requested instalment of INR 14,183.94 exceeds affordable limit of INR 8,945.00", "source": "AFFORDABILITY_ENGINE"}],
    "missing_information": ["Credit bureau history is unavailable on file (thin-file applicant)"],
    "review_flags": ["RESTRUCTURING_RECOMMENDED"]
  }
  ```
- **Affordability basis:** essential expenses are income minus net operating income; nothing on file counts as bank-verified, so the protected buffer is max(INR 3,000, 15% of income) x 1.15 at 50-84% completeness or a partial record. `status` is `SUFFICIENT` (INR 3,000 or more to spare), `BORDERLINE` (under 3,000) or `INSUFFICIENT` (0 or less). `binding_rule` is the cap that sets the largest affordable EMI: `DISPOSABLE_INCOME`, `ITI_FOIR_CAP` or `DTI_CAP`. No financial data on file is zero income, flagged in `missing_information`, never imputed.
- **Reason codes:** every factor's code in order, then `STRESS_TEST_<rating>` when the stress test ran.
- **Status:** 200 OK; 404 unknown application.

### Get assessment
- **Method + path:** `GET /api/v1/assessments/{id}`
- **Response:** the stored side-by-side record: `bureau` (`status`, `score`, `source`), `vouch` (`vouch_score`, `status`, `confidence`, `eligible_endorsements`, `raw_support`, `quality_factor`, all decimal strings or literals), `affordability` (the same fields as above, `binding_constraint` for the rule), `data_quality`, the factor lists and `algorithm_version`.
- **Status:** 200 OK; 404 unknown assessment.

### Run counterfactual scenario
- **Method + path:** `POST /api/v1/assessments/{id}/scenarios`
- **Request:** every field optional; anything left out keeps the assessment's own value (the borrower's income, expenses and debt, the application's principal, tenure and rate, and the dual-axis limit), so `{}` reproduces the assessment.
  ```json
  {
    "simulated_income": "30000.00",
    "simulated_expenses": "15000.00",
    "simulated_principal": "60000.00",
    "simulated_tenure": 24
  }
  ```
- **Response:**
  ```json
  {
    "base_assessment_id": "ASM_4AC19E0AFA3D",
    "is_feasible": true,
    "monthly_emi": "3172.27",
    "residual_cash": "9827.73",
    "income_shock_margin": "0.00",
    "binding_constraint": "NONE",
    "summary": "The requested plan of INR 60,000.00 over 24 months is affordable."
  }
  ```
- **Status:** 200 OK; 404 unknown assessment or its application.

---

## 4. Recourse and audit endpoints

### File borrower dispute
- **Method + path:** `POST /api/v1/endorsements/{id}/dispute`
- **Request:**
  ```json
  {
    "record_id": "TX_999",
    "record_type": "TRANSACTION",
    "reason": "Contested duplicate charge in debt statement",
    "borrower_id": "LAKSHMI"
  }
  ```
  `borrower_id` is optional when `{id}` is an endorsement on file: its recipient is the borrower.
- **Response:**
  ```json
  {
    "dispute_id": "DISP_20261025_001",
    "target_record_id": "TX_999",
    "status": "OPEN",
    "created_at": "2026-10-25T07:30:00Z"
  }
  ```
- **Status:** 201 Created; 400 when neither names a borrower.

### Health check
- **Method + path:** `GET /health`
- **Response:**
  ```json
  {
    "status": "OK",
    "version": "2.0.0",
    "timestamp": "2026-10-25T07:30:00Z"
  }
  ```
- **Status:** 200 OK

---

## 5. Users, loans and graph

### List users
- **Method + path:** `GET /api/v1/users`
- **Response:** a list of `{"user_id": "LAKSHMI", "name": "Lakshmi Naik (Tailoring unit, Hubballi)", "reputation": "0.0", "capacity": "0.0", "status": "ACTIVE", "is_anchor": false, "n_settled_loans": 0}`.
- **Status:** 200 OK

### Create user
- **Method + path:** `POST /api/v1/users`
- **Request:** `{"user_id": "DAVE", "name": "Dave", "reputation": "0.0", "monthly_income": "45000.00", "monthly_debt": "8000.00", "net_operating_income": "30000.00"}` (financial fields optional).
- **Response:** the user, as in the list.
- **Status:** 201 Created

### List loans
- **Method + path:** `GET /api/v1/loans`
- **Response:** a list of `{"loan_id": "LN_00001", "borrower_id": "LAKSHMI", "lender_id": null, "principal": "150000", "outstanding_balance": "150000", "interest_rate": "0.24", "tenure_months": 24, "status": "ACTIVE"}`.
- **Status:** 200 OK

### Repay a loan
- **Method + path:** `POST /api/v1/loans/repay`
- **Request:** `{"loan_id": "LN_00001", "amount": "7930.66"}`
- **Response:** `{"loan_id": "LN_00001", "status": "ACTIVE", "outstanding_balance": "142069.34"}`
- **Status:** 200 OK; 400 on an unknown or closed loan.

### Record a default
- **Method + path:** `POST /api/v1/loans/{id}/default`
- **Request:** `{"delta0": "10"}` (optional; the configured `DEFAULT_BASE_SLASH` otherwise).
- **Response:** the damped cascade, k = 0 defaulter, k = 1 direct sponsors (0.5 x W x delta0), k = 2 their sponsors (0.25 x delta0), nothing beyond:
  ```json
  {
    "loan_id": "LN_00001",
    "status": "DEFAULTED",
    "delta0": "10",
    "penalties": [
      {"user_id": "LAKSHMI", "level": 0, "reputation_before": "0.0", "reputation_after": "-10.0", "status_after": "DEFAULTED"},
      {"user_id": "RAMESH", "level": 1, "reputation_before": "8.0", "reputation_after": "-32.00", "status_after": "RESTRICTED"},
      {"user_id": "SAHYOG", "level": 2, "reputation_before": "20.0", "reputation_after": "17.50", "status_after": "ACTIVE"}
    ]
  }
  ```
- **Status:** 200 OK; 400 if the loan is not active; 404 unknown loan; 422 bad `delta0`.

### Trust graph
- **Method + path:** `GET /api/v1/graph`
- **Response:** `{"nodes": [{"id": "MEENA", "name": "...", "reputation": "10.0", "capacity": "10.0", "status": "ACTIVE", "is_anchor": false}], "edges": [{"source": "MEENA", "target": "SURESH", "weight": "10.0"}]}`
- **Status:** 200 OK

---

## 6. Community endpoints
In memory and reseeded on restart. There is no login yet: the caller names the viewer, voucher or owner. Stakes are reputation points, never money. Scores use the Vouch proposal's formula with tau 3 and lambda 1 (`backend/src/veritrust/community.py`).

### Members
- **Method + path:** `GET /api/v1/community/members`
- **Response:** a list of `{"id": "MEENA", "name": "Meena Patil", "line": "Kirana store, Old Hubballi", "reputation": "82", "budget": "100", "committed": "35", "free": "65", "resolved": 7, "repaid": 6, "track_record": "0.7778"}`.
- **Status:** 200 OK

### Asks
- **Method + path:** `GET /api/v1/community/asks?viewer_id=MEENA` and `GET /api/v1/community/asks/{id}?viewer_id=MEENA`
- **Response:** one ask (or a list):
  ```json
  {
    "id": "LAKSHMI",
    "owner_id": "LAKSHMI",
    "name": "Lakshmi Naik",
    "trade": "Tailoring unit",
    "place": "Hubballi",
    "circle": "Tailors' Association",
    "purpose": "Two industrial sewing machines",
    "amount_band": "₹1–2 lakh",
    "posted_days": 2,
    "story": "Wedding-season orders are more than two machines can stitch...",
    "verified": [{"key": "income", "label": "Income steady for 24 months", "detail": "About ₹38,000 a month · bank statement", "tone": "ok", "shown": true}],
    "thin_file": true,
    "bureau_status": "NO_FILE",
    "bureau_trail": null,
    "expected_repay": "0.80",
    "vouches": [{"voucher_id": "RAMESH", "kind": "KNOWN", "stake": "15", "relationship": "TRADE", "years_known": 6, "utilisation": "0.4000", "weight": "0.3036"}],
    "score": {"score": "16.0", "known_weight": "0.3036", "evidence_weight": "0.2205", "evidence_counted": "0.2205", "total_weight": "0.5241"},
    "setback": null,
    "known_by": ["MEENA", "RAMESH", "KAVYA"],
    "viewer_knows": true
  }
  ```
  Strangers get only the `verified` items the owner shows; the owner gets all. `score.score` is `null` when nobody has vouched: insufficient evidence, never 0.
- **Status:** 200 OK; 404 unknown ask.

### Preview a vouch
- **Method + path:** `POST /api/v1/community/asks/{id}/vouch-preview`
- **Request:** `{"voucher_id": "MEENA", "kind": "KNOWN", "stake": "15", "relationship": "NEIGHBOUR", "years_known": 9}`. `EVIDENCE` vouches omit the relationship.
- **Response:** `{"weight": "0.2971", "utilisation": "0.5000", "score_before": "16.0", "score_after": "23.9", "gain_if_repaid": "0.59", "loss_if_default": "-2.38"}`
- **Status:** 200 OK; 400 when the vouch is not allowed (own ask, already vouching, over budget, KNOWN without a relationship, EVIDENCE with nothing shown).

### Vouch
- **Method + path:** `POST /api/v1/community/asks/{id}/vouches`
- **Request:** as the preview, plus `"read_verified": true` for an `EVIDENCE` vouch.
- **Response:** the ask, as the voucher sees it, with the vouch staked at its current utilisation.
- **Status:** 201 Created; 400 as the preview, or an evidence vouch without `read_verified`; 404 unknown ask.

### Post a setback
- **Method + path:** `POST /api/v1/community/asks/{id}/setback`
- **Request:** `{"text": "Hospital bill not covered by insurance..."}`
- **Response:** the ask, with `setback.responses` set to `PENDING` for every KNOWN voucher.
- **Status:** 200 OK; 400 empty text.

### Stand by or step back
- **Method + path:** `POST /api/v1/community/asks/{id}/setback/respond`
- **Request:** `{"voucher_id": "MEENA", "choice": "STAND_BY"}` (`STEP_BACK` withdraws the vouch and frees the stake).
- **Response:** the ask.
- **Status:** 200 OK; 400 if the voucher has no response pending.

### Show or hide a verified item
- **Method + path:** `POST /api/v1/community/asks/{id}/verified/{key}`
- **Request:** `{"shown": false}`
- **Response:** the ask, as its owner sees it.
- **Status:** 200 OK; 404 unknown ask or item.
