"""Unit tests for the tuned rule-based underwriting and explanation fallback engine.

Verifies:
1. Rule-based cash-flow affordability and DTI bounds.
2. Calibrated default probability and Basel scorecard rating bounds.
3. Split-conformal prediction sets under fallback execution.
4. Explainability factor generation and counterfactual remedy recommendations.
5. Fail-safe invocation via /api/v1/predict when ML crashes or force_fallback is set.
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from veritrust.api.app import app
from veritrust.api.deps import get_services, reset_services
from veritrust.prediction import predict_with_fallback
from veritrust.rule_fallback import RuleBasedFallbackEngine


@pytest.fixture(autouse=True)
def setup_services():
    """Ensure clean service state before each test."""
    reset_services()


@pytest.fixture
def client():
    return TestClient(app)


def test_rule_fallback_engine_eligible():
    """Verify RuleBasedFallbackEngine produces an ELIGIBLE assessment for healthy borrower."""
    engine = RuleBasedFallbackEngine()
    params = {
        "monthly_income": "60000.00",
        "monthly_debt": "3000.00",
        "net_operating_income": "35000.00",
        "requested_amount": "50000.00",
        "requested_tenure_months": 12,
        "annual_interest_rate": 0.15,
        "vouch_count": 3,
        "vouch_score": "75.0",
        "bureau_status": "NO_FILE",
        "bank_bounces_3m": 0,
    }
    result = engine.evaluate(params)

    assert result["is_fallback"] is True
    assert result["model_source"] == "RULE_BASED_FALLBACK"
    pred = result["prediction"]
    assert pred["decision"] == "ELIGIBLE"
    assert "REPAY" in pred["conformal_set"]
    assert 650 <= pred["credit_score"] <= 900
    assert pred["default_probability"] < 0.15
    assert pred["repayment_probability"] > 0.85

    # Multi-dimensional scores
    multi = result["multidimensional_scores"]
    assert multi["financial_capacity_score"] > 70.0
    assert multi["graph_reputation_score"] == 75.0

    # Explanation items
    expl = result["explanation"]
    assert len(expl["positive_factors"]) >= 2
    assert len(expl["summary"]) > 0


def test_rule_fallback_engine_decline_excessive_debt():
    """Verify RuleBasedFallbackEngine flags DECLINE_CANDIDATE when debt exceeds prudent cap."""
    engine = RuleBasedFallbackEngine()
    params = {
        "monthly_income": "25000.00",
        "monthly_debt": "15000.00",  # 60% DTI before new loan
        "net_operating_income": "5000.00",
        "requested_amount": "200000.00",
        "requested_tenure_months": 6,
        "annual_interest_rate": 0.20,
        "vouch_count": 0,
        "bank_bounces_3m": 2,
    }
    result = engine.evaluate(params)

    assert result["is_fallback"] is True
    pred = result["prediction"]
    assert pred["decision"] == "DECLINE_CANDIDATE"
    assert "DEFAULT" in pred["conformal_set"]
    assert pred["default_probability"] > 0.25
    assert pred["credit_score"] < 600

    # Risk factors present
    expl = result["explanation"]
    assert len(expl["risk_factors"]) >= 2

    # Counterfactual remedies suggest extending tenure or reducing principal
    remedy = result["counterfactual_remedy"]
    assert remedy["is_already_eligible"] is False
    assert len(remedy["actionable_recommendations"]) > 0


def test_predict_with_fallback_forced():
    """Verify predict_with_fallback cleanly returns rule-based fallback when force_fallback=True."""
    engine, scorer, _, _ = get_services()
    params = {
        "borrower_id": "LAKSHMI",
        "requested_amount": "80000.00",
        "requested_tenure_months": 12,
    }
    result = predict_with_fallback(params, engine=engine, scorer=scorer, force_fallback=True)
    assert result["is_fallback"] is True
    assert result["model_source"] == "RULE_BASED_FALLBACK"
    assert "Explicit rule-based fallback requested" in result["fallback_reason"]
    assert result["prediction"]["decision"] in ("ELIGIBLE", "REVIEW", "DECLINE_CANDIDATE")


def test_predict_with_fallback_exception_handling(monkeypatch):
    """Verify predict_with_fallback intercepts ML runtime crash and returns fallback."""
    import veritrust.prediction as pred_module

    def mock_crash(*args, **kwargs):
        raise RuntimeError("Simulated ML model weight failure / CUDA out of memory")

    monkeypatch.setattr(pred_module, "evaluate_credit_prediction", mock_crash)

    engine, scorer, _, _ = get_services()
    params = {
        "borrower_id": "LAKSHMI",
        "requested_amount": "80000.00",
        "requested_tenure_months": 12,
    }
    result = predict_with_fallback(params, engine=engine, scorer=scorer)
    assert result["is_fallback"] is True
    assert result["model_source"] == "RULE_BASED_FALLBACK"
    assert "Simulated ML model weight failure" in result["fallback_reason"]
    assert result["prediction"]["credit_score"] >= 300


def test_api_predict_force_fallback(client):
    """Verify POST /api/v1/predict with force_fallback=true returns 200 with fallback payload."""
    payload = {
        "borrower_id": "LAKSHMI",
        "requested_amount": "50000.00",
        "requested_tenure_months": 12,
        "force_fallback": True,
    }
    res = client.post("/api/v1/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_fallback"] is True
    assert data["model_source"] == "RULE_BASED_FALLBACK"
    assert data["prediction"]["decision"] in ("ELIGIBLE", "REVIEW", "DECLINE_CANDIDATE")
    assert 300 <= data["prediction"]["credit_score"] <= 900
