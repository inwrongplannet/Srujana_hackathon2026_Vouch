# API Contract

**Why this file exists:** Abhishek writes endpoint shapes here *before* anyone implements them, so frontend and backend can be built in parallel without waiting on each other.

## Overview
All endpoints accept and return `application/json`. Timestamps follow ISO 8601 UTC. Monetary amounts are strings in INR minor units or decimal numbers with two decimal places.

---

## 1. Application endpoints

### Create loan application
- **Method + path:** `POST /api/v1/applications`
- **Request:**
  ```json
  {
    "borrower_id": "BOB",
    "principal": "50000.00",
    "annual_rate": 0.12,
    "term_months": 12,
    "purpose_category": "WORKING_CAPITAL"
  }
  ```
- **Response:**
  ```json
  {
    "application_id": "APP_20261025_001",
    "borrower_id": "BOB",
    "principal": "50000.00",
    "term_months": 12,
    "status": "SUBMITTED",
    "created_at": "2026-10-25T07:30:00Z"
  }
  ```
- **Status:** 201 Created

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
    "application_id": "APP_20261025_001",
    "status": "REGISTERED",
    "verified_at": "2026-10-25T07:30:00Z"
  }
  ```
- **Status:** 201 Created

---

## 2. Endorsement endpoints

### Issue peer endorsement
- **Method + path:** `POST /api/v1/endorsements`
- **Request:**
  ```json
  {
    "endorser_id": "ALICE",
    "recipient_id": "BOB",
    "application_id": "APP_20261025_001",
    "statement": "Vouching for Bob based on 3 years of trade partnership"
  }
  ```
- **Response:**
  ```json
  {
    "endorsement_id": "VOUCH_ALICE_BOB",
    "endorser_id": "ALICE",
    "recipient_id": "BOB",
    "allocated_weight": "10.0",
    "status": "ACTIVE",
    "created_at": "2026-10-25T07:30:00Z"
  }
  ```
- **Status:** 201 Created

### Get user vouch summary
- **Method + path:** `GET /api/v1/users/{id}/vouch-summary`
- **Response:**
  ```json
  {
    "user_id": "BOB",
    "vouch_score": 74.0,
    "confidence_rating": "HIGH",
    "eligible_endorsement_count": 3,
    "reputation_capacity": "15.0",
    "active_incoming_paths": 2
  }
  ```
- **Status:** 200 OK

---

## 3. Assessment and optimization endpoints

### Run credit assessment & optimization
- **Method + path:** `POST /api/v1/applications/{id}/assessments`
- **Request:**
  ```json
  {
    "objective": "MIN_COST",
    "enable_stress_test": true,
    "simulation_scenarios": 5000
  }
  ```
- **Response:**
  ```json
  {
    "assessment_id": "ASM_20261025_001",
    "application_id": "APP_20261025_001",
    "borrower_id": "BOB",
    "verdict": "APPROVED",
    "bureau_status": "NO_FILE",
    "bureau_score": null,
    "affordability": {
      "gross_monthly_income": "35000.00",
      "non_discretionary_outflows": "19000.00",
      "disposable_income": "10750.00",
      "max_affordable_emi": "10750.00",
      "status": "SUFFICIENT"
    },
    "best_plan": {
      "principal": "50000.00",
      "term_months": 12,
      "monthly_emi": "4395.79",
      "total_interest": "2749.48"
    },
    "stress_resilience": {
      "rating": "RESILIENT",
      "shortfall_probability": 0.0256,
      "adverse_5th_percentile_cash": "2716.92",
      "income_shock_tolerance_percent": 36.01
    },
    "reason_codes": [
      "DISPOSABLE_INCOME_SUFFICIENT",
      "CAPACITY_LIMIT_QUALIFIED",
      "STRESS_TEST_RESILIENT"
    ]
  }
  ```
- **Status:** 200 OK

### Run counterfactual scenario
- **Method + path:** `POST /api/v1/assessments/{id}/scenarios`
- **Request:**
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
    "base_assessment_id": "ASM_20261025_001",
    "is_feasible": true,
    "monthly_emi": "2768.70",
    "residual_cash": "7731.30",
    "income_shock_margin": "1250.00",
    "binding_constraint": "DISPOSABLE_INCOME"
  }
  ```
- **Status:** 200 OK

---

## 4. Recourse and audit endpoints

### File borrower dispute
- **Method + path:** `POST /api/v1/endorsements/{id}/dispute`
- **Request:**
  ```json
  {
    "record_id": "TX_999",
    "record_type": "TRANSACTION",
    "reason": "Contested duplicate charge in debt statement"
  }
  ```
- **Response:**
  ```json
  {
    "dispute_id": "DISP_20261025_001",
    "target_record_id": "TX_999",
    "status": "OPEN",
    "created_at": "2026-10-25T07:30:00Z"
  }
  ```
- **Status:** 201 Created

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
