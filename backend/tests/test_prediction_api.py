"""Tests for the predictive risk and explainability API endpoints (/api/v1/predict)."""

import pytest
from fastapi.testclient import TestClient

from veritrust.api.app import app
from veritrust.api.deps import reset_services


@pytest.fixture(autouse=True)
def setup_services():
    """Ensure clean service state before each test."""
    reset_services()


@pytest.fixture
def client():
    return TestClient(app)


def test_predict_sample_endpoint(client):
    """Verify GET /api/v1/predict/sample returns valid sample request payload."""
    res = client.get("/api/v1/predict/sample")
    assert res.status_code == 200
    data = res.json()
    assert data["borrower_id"] == "LAKSHMI"
    assert "monthly_income" in data
    assert "requested_amount" in data
    assert data["bureau_status"] == "NO_FILE"


def test_predict_existing_borrower_lakshmi(client):
    """Verify POST /api/v1/predict using existing borrower ID."""
    payload = {
        "borrower_id": "LAKSHMI",
        "requested_amount": "100000.00",
        "requested_tenure_months": 12,
    }
    res = client.post("/api/v1/predict", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["borrower_id"] == "LAKSHMI"
    # Prediction details
    pred = data["prediction"]
    assert 0.0 <= pred["default_probability"] <= 1.0
    assert 0.0 <= pred["repayment_probability"] <= 1.0
    assert 300 <= pred["credit_score"] <= 900
    assert pred["decision"] in ("ELIGIBLE", "REVIEW", "DECLINE_CANDIDATE")
    assert len(pred["conformal_set"]) >= 1
    assert pred["risk_tier"] in ("LOW_RISK", "MODERATE_RISK", "HIGH_RISK", "VERY_HIGH_RISK")

    # Explanation details
    expl = data["explanation"]
    assert len(expl["summary"]) > 0
    assert isinstance(expl["positive_factors"], list)
    assert isinstance(expl["risk_factors"], list)
    assert len(expl["positive_factors"]) + len(expl["risk_factors"]) > 0

    # Every factor has code, text, log_odds, and direction
    for factor in expl["positive_factors"] + expl["risk_factors"]:
        assert "code" in factor
        assert "text" in factor
        assert "log_odds" in factor
        assert factor["direction"] in ("raises_risk", "lowers_risk")

    # Multi-dimensional scores
    multi = data["multidimensional_scores"]
    assert 0.0 <= multi["financial_capacity_score"] <= 100.0
    assert 0.0 <= multi["evidence_reliability_score"] <= 100.0
    assert 0.0 <= multi["graph_reputation_score"] <= 100.0
    assert 0.0 <= multi["stress_resilience_score"] <= 100.0

    # Temporal freshness
    tf = data["temporal_freshness"]
    assert tf["evidence_age_months"] == 0.0
    assert tf["vouch_confidence"] == 1.0
    assert tf["is_stale"] is False

    # Counterfactual remedies
    remedy = data["counterfactual_remedy"]
    assert remedy["target_decision"] == "ELIGIBLE"
    assert "max_recommended_principal" in remedy
    assert len(remedy["actionable_recommendations"]) > 0


def test_predict_unknown_borrower_raises_404(client):
    """Verify unknown borrower_id returns 404 Not Found."""
    payload = {
        "borrower_id": "UNKNOWN_BORROWER_999",
        "requested_amount": "50000.00",
    }
    res = client.post("/api/v1/predict", json=payload)
    assert res.status_code == 404
    assert "UNKNOWN_BORROWER_999" in res.json()["detail"]


def test_predict_standalone_profile_without_borrower_id(client):
    """Verify predicting for a new applicant without pre-registered ID."""
    payload = {
        "monthly_income": "45000.00",
        "monthly_debt": "3000.00",
        "net_operating_income": "28000.00",
        "requested_amount": "120000.00",
        "requested_tenure_months": 24,
        "annual_interest_rate": 0.16,
        "vouch_count": 3,
        "vouch_score": "75.0",
        "bank_income_cv": 0.08,
        "bank_statement_status": "VERIFIED",
    }
    res = client.post("/api/v1/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"]["decision"] == "ELIGIBLE"
    assert data["prediction"]["credit_score"] >= 700
    assert data["counterfactual_remedy"]["is_already_eligible"] is True


def test_predict_delinquent_candidate(client):
    """Verify high-delinquency applicant is classified as DECLINE_CANDIDATE with counterfactual guidance."""
    payload = {
        "monthly_income": "25000.00",
        "monthly_debt": "15000.00",
        "requested_amount": "300000.00",
        "requested_tenure_months": 12,
        "bureau_max_dpd_24m": 90,
        "bureau_written_off": 1,
        "bank_bounces_3m": 3,
        "vouch_count": 0,
        "vouch_score": "0.0",
    }
    res = client.post("/api/v1/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"]["decision"] == "DECLINE_CANDIDATE"
    assert data["prediction"]["risk_tier"] == "VERY_HIGH_RISK"
    assert data["prediction"]["default_probability"] > 0.50

    remedy = data["counterfactual_remedy"]
    assert remedy["is_already_eligible"] is False
    assert len(remedy["actionable_recommendations"]) >= 2


def test_predict_temporal_evidence_staleness(client):
    """Verify evidence age inflation increases epistemic uncertainty and triggers staleness warning."""
    fresh_payload = {
        "monthly_income": "40000.00",
        "requested_amount": "100000.00",
        "vouch_count": 2,
        "vouch_score": "50.0",
        "evidence_age_months": 0.0,
    }
    stale_payload = {
        **fresh_payload,
        "evidence_age_months": 24.0,  # 2 years stale
    }

    res_fresh = client.post("/api/v1/predict", json=fresh_payload).json()
    res_stale = client.post("/api/v1/predict", json=stale_payload).json()

    assert res_fresh["temporal_freshness"]["is_stale"] is False
    assert res_stale["temporal_freshness"]["is_stale"] is True
    assert res_stale["temporal_freshness"]["staleness_warning"] is not None
    assert res_stale["temporal_freshness"]["vouch_confidence"] < res_fresh["temporal_freshness"]["vouch_confidence"]

    # Epistemic uncertainty inflated
    assert res_stale["prediction"]["epistemic_uncertainty"] > res_fresh["prediction"]["epistemic_uncertainty"]


def test_predict_missing_information_disclosures(client):
    """Verify STATUS_GAPS disclosures are captured in missing_information list."""
    payload = {
        "monthly_income": "30000.00",
        "bank_statement_status": "NOT_PROVIDED",
        "bureau_status": "NO_FILE",
        "gst_status": "PARTIAL",
        "declared_income_status": "WITHHELD",
    }
    res = client.post("/api/v1/predict", json=payload)
    assert res.status_code == 200
    missing = res.json()["explanation"]["missing_information"]
    codes = [m["code"] for m in missing]
    assert "MISSING_BANK_STATEMENT" in codes
    assert "MISSING_BUREAU_FILE" in codes
    assert "MISSING_GST" in codes
    assert "MISSING_DECLARED_INCOME" in codes
