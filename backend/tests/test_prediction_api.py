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



def _predict(client, **body):
    base = {"requested_amount": "150000.00", "requested_tenure_months": 12, "annual_interest_rate": 0.24}
    res = client.post("/api/v1/predict", json={**base, **body})
    assert res.status_code == 200
    return res.json()


def test_predict_never_eligible_when_the_emi_does_not_fit(client):
    """Same affordability basis as the assessment: Lakshmi can afford INR 8,945 a month."""
    # 1,50,000 at 24% over 12 months: EMI 14,183.94 > 8,945.00, so not eligible on these terms.
    d = _predict(client, borrower_id="LAKSHMI")
    assert d["prediction"]["decision"] == "DECLINE_CANDIDATE"
    assert d["counterfactual_remedy"]["sustainable_emi"] == "8945.00"
    assert "14,183.94" in d["explanation"]["summary"]
    # Over 24 months the EMI is 7,930.66, which fits.
    d24 = _predict(client, borrower_id="LAKSHMI", requested_tenure_months=24)
    assert d24["prediction"]["decision"] == "ELIGIBLE"


def test_predict_undocumented_expenses_use_the_fixed_allowance(client):
    """Imran has no net operating income on file: expenses are the INR 10,000 allowance, not a share of income."""
    d = _predict(client, borrower_id="IMRAN")
    assert d["prediction"]["decision"] != "ELIGIBLE"
    assert d["counterfactual_remedy"]["sustainable_emi"] == "8205.00"


def test_predict_uncertainty_follows_evidence_depth(client):
    """sigma2 = 1 / (1 + N x completeness): Lakshmi N = 2 vouches + financials = 3 at 0.90; Imran N = 1 at 0.75."""
    assert _predict(client, borrower_id="LAKSHMI")["prediction"]["epistemic_uncertainty"] == pytest.approx(0.2703, abs=1e-4)
    assert _predict(client, borrower_id="IMRAN")["prediction"]["epistemic_uncertainty"] == pytest.approx(0.5714, abs=1e-4)


def test_predict_vouch_count_matches_the_vouch_score(client):
    """Count and score come from one report: Lakshmi's seed vouches (Ramesh, Anand) are 2 eligible endorsements."""
    d = _predict(client, borrower_id="LAKSHMI")
    texts = [f["text"] for f in d["explanation"]["positive_factors"] + d["explanation"]["risk_factors"]]
    assert "Community peer vouches: 2" in texts
    assert d["multidimensional_scores"]["graph_reputation_score"] > 0


def test_predict_missing_bureau_is_not_a_clean_record(client):
    """No bureau file: no bureau factor is scored; a sent value is."""
    codes = lambda d: {f["code"] for f in d["explanation"]["positive_factors"] + d["explanation"]["risk_factors"]}
    d = _predict(client, borrower_id="LAKSHMI", bureau_status="NO_FILE")
    assert not {c for c in codes(d) if c.startswith("BUREAU_")}
    assert "MISSING_BUREAU_FILE" in {m["code"] for m in d["explanation"]["missing_information"]}
    sent = _predict(client, borrower_id="LAKSHMI", bureau_status="AVAILABLE", bureau_max_dpd_24m=0)
    assert "BUREAU_DELINQUENCY" in codes(sent)


def test_predict_stress_resilience_is_continuous(client):
    """After a 20% income fall Lakshmi has 30,400 - 20,500 - 2,000 = 7,900 for a 14,183.94 EMI: 30 x 0.557 = 16.7."""
    d = _predict(client, borrower_id="LAKSHMI")
    assert d["multidimensional_scores"]["stress_resilience_score"] == pytest.approx(16.7, abs=0.05)
