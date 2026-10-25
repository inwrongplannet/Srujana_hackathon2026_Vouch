"""Vouch requests, lender decisions, defaults and the community API.

These routers never import the OR-Tools optimizer, so they are tested on an app that mounts only
them; applications are placed in the shared registry directly.
"""

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from veritrust.api import registry
from veritrust.api.community_routes import reset_community
from veritrust.api.community_routes import router as community_router
from veritrust.api.deps import reset_services
from veritrust.api.protocol_routes import _requests
from veritrust.api.protocol_routes import router as protocol_router
from veritrust.models import LoanApplication


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Keep the committed backend/data/store.json untouched: the store writes to a temp folder.
    from veritrust.api import deps
    from veritrust.store import StateStore

    monkeypatch.setattr(deps, "_store", StateStore(data_dir=tmp_path))
    reset_services()
    reset_community()
    _requests.clear()
    registry.applications.clear()
    app = FastAPI()
    app.include_router(protocol_router)
    app.include_router(community_router)
    return TestClient(app)


def _application(app_id: str, borrower: str, principal: str, term: int = 12) -> None:
    registry.applications[app_id] = LoanApplication(
        application_id=app_id, borrower_id=borrower, principal=Decimal(principal),
        annual_rate=Decimal("0.24"), term_months=term,
    )


def test_vouch_request_accept_creates_endorsement(client):
    res = client.post("/api/v1/vouch-requests", json={"requester_id": "LAKSHMI", "voucher_id": "MEENA", "note": "Neighbour of 9 years"})
    assert res.status_code == 201
    req_id = res.json()["request_id"]
    assert client.post("/api/v1/vouch-requests", json={"requester_id": "LAKSHMI", "voucher_id": "MEENA"}).status_code == 409
    pending = client.get("/api/v1/vouch-requests", params={"voucher_id": "MEENA", "status": "PENDING"}).json()
    assert [r["request_id"] for r in pending] == [req_id]

    accepted = client.post(f"/api/v1/vouch-requests/{req_id}/respond", json={"accept": True}).json()
    assert accepted["status"] == "ACCEPTED"
    assert accepted["endorsement_id"] == "V_MEENA_LAKSHMI"
    assert client.post(f"/api/v1/vouch-requests/{req_id}/respond", json={"accept": False}).status_code == 409


def test_vouch_request_rejects_self_and_unknown(client):
    assert client.post("/api/v1/vouch-requests", json={"requester_id": "LAKSHMI", "voucher_id": "LAKSHMI"}).status_code == 400
    assert client.post("/api/v1/vouch-requests", json={"requester_id": "LAKSHMI", "voucher_id": "NOBODY"}).status_code == 404
    # Ramesh already vouches for Lakshmi in the seed.
    assert client.post("/api/v1/vouch-requests", json={"requester_id": "LAKSHMI", "voucher_id": "RAMESH"}).status_code == 409


def test_decision_approve_then_default_runs_the_cascade(client):
    _application("APP_T1", "LAKSHMI", "50000")
    res = client.post("/api/v1/applications/APP_T1/decision", json={"decision": "APPROVE"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "APPROVED"
    loan_id = body["loan"]["loan_id"]
    assert body["loan"]["principal"] == "50000"
    assert client.post("/api/v1/applications/APP_T1/decision", json={"decision": "DECLINE"}).status_code == 409

    cascade = client.post(f"/api/v1/loans/{loan_id}/default", json={"delta0": "10"}).json()
    assert cascade["status"] == "DEFAULTED"
    by_user = {p["user_id"]: p for p in cascade["penalties"]}
    # k=0 Lakshmi: 0 - 10. k=1 Ramesh (W 8) and Anand (W 6): 0.5 * W * 10. k=2 Sahyog: 0.25 * 10.
    assert by_user["LAKSHMI"]["level"] == 0 and Decimal(by_user["LAKSHMI"]["reputation_after"]) == Decimal(-10)
    assert by_user["LAKSHMI"]["status_after"] == "DEFAULTED"
    assert Decimal(by_user["RAMESH"]["reputation_after"]) == Decimal(8) - Decimal(40)
    assert Decimal(by_user["ANAND"]["reputation_after"]) == Decimal(6) - Decimal(30)
    assert by_user["SAHYOG"]["level"] == 2
    assert Decimal(by_user["SAHYOG"]["reputation_after"]) == Decimal(20) - Decimal("2.5")
    assert "MEENA" not in by_user  # k >= 3 or unrelated: untouched


def test_decision_over_limit_is_refused_and_at_limit_is_capped(client):
    _application("APP_BIG", "LAKSHMI", "900000")
    assert client.post("/api/v1/applications/APP_BIG/decision", json={"decision": "APPROVE"}).status_code == 400
    capped = client.post("/api/v1/applications/APP_BIG/decision", json={"decision": "APPROVE_AT_LIMIT"}).json()
    assert Decimal(capped["loan"]["principal"]) < Decimal(900000)
    _application("APP_IMRAN", "IMRAN", "20000")
    # Imran has no vouches yet, so his limit is 0: nothing can be offered.
    assert client.post("/api/v1/applications/APP_IMRAN/decision", json={"decision": "APPROVE_AT_LIMIT"}).status_code == 400


def test_community_feed_hides_unshown_items_from_strangers(client):
    assert client.post("/api/v1/community/asks/LAKSHMI/verified/rent", json={"shown": False}).status_code == 200
    stranger = client.get("/api/v1/community/asks/LAKSHMI", params={"viewer_id": "ANAND"}).json()
    owner = client.get("/api/v1/community/asks/LAKSHMI", params={"viewer_id": "LAKSHMI"}).json()
    assert "rent" not in [v["key"] for v in stranger["verified"]]
    assert "rent" in [v["key"] for v in owner["verified"]]
    imran = client.get("/api/v1/community/asks/IMRAN").json()
    assert imran["score"]["score"] is None  # nobody has vouched: no score, not zero


def test_community_preview_matches_the_vouch(client):
    body = {"voucher_id": "MEENA", "kind": "KNOWN", "stake": "15", "relationship": "NEIGHBOUR", "years_known": 9}
    preview = client.post("/api/v1/community/asks/LAKSHMI/vouch-preview", json=body).json()
    # Known answer: 0.82 * (7/9) * e^-0.5 * 0.768 = 0.2971 (U = (35 + 15) / 100 = 0.5).
    assert preview["weight"] == "0.2971"
    assert preview["utilisation"] == "0.5000"
    after = client.post("/api/v1/community/asks/LAKSHMI/vouches", json=body)
    assert after.status_code == 201
    assert after.json()["score"]["score"] == preview["score_after"]
    assert Decimal(preview["gain_if_repaid"]) > 0 > Decimal(preview["loss_if_default"])
    members = {m["id"]: m for m in client.get("/api/v1/community/members").json()}
    assert members["MEENA"]["committed"] == "50"


def test_community_rejects_bad_vouches(client):
    over = {"voucher_id": "MEENA", "kind": "KNOWN", "stake": "70", "relationship": "NEIGHBOUR", "years_known": 9}
    assert client.post("/api/v1/community/asks/LAKSHMI/vouches", json=over).status_code == 400
    unread = {"voucher_id": "FARIDA", "kind": "EVIDENCE", "stake": "5"}
    assert client.post("/api/v1/community/asks/LAKSHMI/vouches", json=unread).status_code == 400
    own = {"voucher_id": "FARIDA", "kind": "EVIDENCE", "stake": "5", "read_verified": True}
    assert client.post("/api/v1/community/asks/FARIDA_ASK/vouches", json=own).status_code == 400
    assert client.post("/api/v1/community/asks/NOPE/vouches", json=own).status_code == 404


def test_setback_stand_by_and_step_back(client):
    stood = client.post("/api/v1/community/asks/SURESH/setback/respond", json={"voucher_id": "MEENA", "choice": "STAND_BY"}).json()
    assert stood["setback"]["responses"]["MEENA"] == "STAND_BY"
    assert "MEENA" in [v["voucher_id"] for v in stood["vouches"]]
    posted = client.post("/api/v1/community/asks/LAKSHMI/setback", json={"text": "Flood stock loss"}).json()
    assert posted["setback"]["responses"] == {"RAMESH": "PENDING"}  # only KNOWN vouchers are asked
    left = client.post("/api/v1/community/asks/LAKSHMI/setback/respond", json={"voucher_id": "RAMESH", "choice": "STEP_BACK"}).json()
    assert "RAMESH" not in [v["voucher_id"] for v in left["vouches"]]
