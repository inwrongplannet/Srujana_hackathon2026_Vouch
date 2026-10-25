"""Integration tests for the Vouch / VeriTrust FastAPI REST API layer."""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from veritrust.affordability import calculate_emi
from veritrust.api.app import app
from veritrust.api.deps import reset_services


@pytest.fixture(autouse=True)
def setup_services():
    """Ensure clean service state before each API test."""
    reset_services()


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    """Verify /health returns 200 OK and version info."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OK"
    assert data["version"] == "2.0.0"


def test_list_and_create_users(client):
    """Verify user registration and retrieval endpoints."""
    # List initial seeded users
    res = client.get("/api/v1/users")
    assert res.status_code == 200
    users = res.json()
    user_ids = [u["user_id"] for u in users]
    assert "SAHYOG" in user_ids
    assert "LAKSHMI" in user_ids

    # Create new user
    create_payload = {
        "user_id": "DAVE",
        "name": "Dave (Tech Freelancer)",
        "reputation": "5.0",
        "monthly_income": "45000.00",
        "monthly_debt": "8000.00",
    }
    res_create = client.post("/api/v1/users", json=create_payload)
    assert res_create.status_code == 201
    assert res_create.json()["user_id"] == "DAVE"


def test_vouch_summary(client):
    """Verify /api/v1/users/{id}/vouch-summary returns Vouch score report."""
    res = client.get("/api/v1/users/LAKSHMI/vouch-summary")
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "LAKSHMI"
    assert isinstance(data["vouch_score"], str)  # a decimal string, as in every assessment
    assert data["confidence_rating"] in ("LOW", "MEDIUM", "HIGH")
    assert data["eligible_endorsement_count"] >= 1


def test_endorsement_creation(client):
    """Verify issuing a peer endorsement via POST /api/v1/endorsements."""
    # Meena endorses Imran
    endorse_payload = {
        "endorser_id": "MEENA",
        "recipient_id": "IMRAN",
        "statement": "Imran has run the stall beside my shop for two years",
    }
    res = client.post("/api/v1/endorsements", json=endorse_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["endorser_id"] == "MEENA"
    assert data["recipient_id"] == "IMRAN"
    assert data["status"] == "ACTIVE"


def test_loan_application_and_assessment_lifecycle(client):
    """Verify full application -> evidence -> assessment flow."""
    # 1. Create loan application
    app_payload = {
        "borrower_id": "LAKSHMI",
        "principal": "50000.00",
        "annual_rate": 0.12,
        "term_months": 12,
        "purpose_category": "WORKING_CAPITAL",
    }
    res_app = client.post("/api/v1/applications", json=app_payload)
    assert res_app.status_code == 201
    app_id = res_app.json()["application_id"]

    # 2. Register evidence
    evid_payload = {
        "evidence_type": "BANK_STATEMENT",
        "source": "ACCOUNT_AGGREGATOR",
        "description": "Verified 6-month statement",
    }
    res_evid = client.post(f"/api/v1/applications/{app_id}/evidence", json=evid_payload)
    assert res_evid.status_code == 201

    # 3. Run assessment
    asm_payload = {
        "objective": "MIN_COST",
        "enable_stress_test": True,
        "simulation_scenarios": 1000,
        "bureau_status": "NO_FILE",
    }
    res_asm = client.post(f"/api/v1/applications/{app_id}/assessments", json=asm_payload)
    assert res_asm.status_code == 200
    asm_data = res_asm.json()
    assert asm_data["borrower_id"] == "LAKSHMI"
    assert asm_data["affordability"]["status"] in ("SUFFICIENT", "BORDERLINE", "INSUFFICIENT")
    assert isinstance(asm_data["vouch_score"], str)
    assert asm_data["reason_codes"]
    assert asm_data["bureau_status"] == "NO_FILE"
    assert asm_data["verdict"] in ("APPROVED", "RESTRUCTURED_ALTERNATIVE")
    assert "stress_resilience" in asm_data
    asm_id = asm_data["assessment_id"]

    # 4. Retrieve stored assessment
    res_get_asm = client.get(f"/api/v1/assessments/{asm_id}")
    assert res_get_asm.status_code == 200
    assert res_get_asm.json()["assessment_id"] == asm_id

    # 5. Run scenario on this assessment
    scenario_payload = {
        "simulated_income": "40000.00",
        "simulated_principal": "30000.00",
    }
    res_scen = client.post(f"/api/v1/assessments/{asm_id}/scenarios", json=scenario_payload)
    assert res_scen.status_code == 200
    scen_data = res_scen.json()
    assert scen_data["base_assessment_id"] == asm_id
    assert "monthly_emi" in scen_data

    # 6. An unchanged what-if reproduces the assessment: same rate, data and limit.
    res_same = client.post(f"/api/v1/assessments/{asm_id}/scenarios", json={})
    assert res_same.status_code == 200
    same = res_same.json()
    assert same["monthly_emi"] == str(calculate_emi(Decimal("50000.00"), Decimal("0.12"), 12))
    assert same["is_feasible"] == (asm_data["verdict"] == "APPROVED")


def test_recourse_dispute_endpoint(client):
    """Verify filing dispute via /api/v1/endorsements/{id}/dispute."""
    dispute_payload = {
        "record_id": "TX_999",
        "record_type": "TRANSACTION",
        "reason": "Contested erroneous charge",
        "borrower_id": "LAKSHMI",
    }
    res = client.post("/api/v1/endorsements/VOUCH_001/dispute", json=dispute_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["target_record_id"] == "TX_999"
    assert data["status"] == "OPEN"


def test_graph_visualization_endpoint(client):
    """Verify /api/v1/graph returns nodes and weighted edges."""
    res = client.get("/api/v1/graph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 3
    assert len(data["edges"]) >= 2
