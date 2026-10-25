"""Shock and vouch dataset: known-answer maths plus the structural validation gates.

The statistical gates (association, dose-response, model increment, placebo, calibration) need
the full dataset and run in `python -m veritrust.synth.shock_validate`; results are recorded in
data/combined/README.md. The gates here hold on any sample size.
"""

import csv
import json
from decimal import Decimal

import pytest
from veritrust.anchor.prosper import build as build_prosper
from veritrust.anchor.prosper import check as check_prosper
from veritrust.anchor.trajectory import trajectory_rows
from veritrust.synth import params as P
from veritrust.synth.bureau import components, score
from veritrust.synth.generate import generate
from veritrust.synth.shock_validate import B1_CATEGORICAL, B1_NUMERIC, BANNED
from veritrust.synth.vouch import Edge, Voucher, edge_weight, outcome_rows, score_at


def _state(**overrides) -> dict:
    state = {"history": 60, "worst_dpd": 0, "late_months": 0, "max_dpd_24m": 0, "written_off": 0,
             "utilisation": Decimal("0.5000"), "enquiries_6m": 0, "new_lines_6m": 0, "active": 1, "outstanding": 0}
    state.update(overrides)
    return state


def test_scorecard_known_answer():
    # 720 base + 30 history (60 of 120 months) - 40 (30 DPD now) - 12 (one late month)
    # - 12 (utilisation 0.90 is 0.20 over the free 0.70, x 60) - 16 (two enquiries) - 10 (one new line) = 660.
    state = _state(worst_dpd=30, late_months=1, utilisation=Decimal("0.9000"), enquiries_6m=2, new_lines_6m=1)
    assert score(state) == 660
    assert components(state)["utilisation"] == -12


def test_scorecard_clean_file_and_floor():
    assert score(_state()) == 750
    assert score(_state(worst_dpd=180, late_months=24, written_off=1, history=0,
                        utilisation=Decimal("1.0"), enquiries_6m=20, new_lines_6m=9)) == 300


def _voucher(reputation="80", reliability="0.9") -> Voucher:
    return Voucher(voucher_id="V1", kind="PERSON", reputation=Decimal(reputation),
                   reliability=Decimal(reliability), budget=Decimal(100), cluster="V1")


def _edge(created=0, ended=None, reciprocal=False, utilisation="0.5", quality="1") -> Edge:
    return Edge(vouch_id="E1", voucher=_voucher(), recipient_id="B1", relationship="FAMILY", months_known=12,
                stake=Decimal(10), utilisation=Decimal(utilisation), quality=Decimal(quality), created=created,
                expiries=[created + 12], ended=ended, reciprocal=reciprocal)


def test_vouch_weight_and_score_known_answer():
    # w = 0.80 * 0.9 * e^-0.5 * 1 = 0.436702 (e^-0.5 = 0.606531); S = 100 * (1 - e^(-0.436702 / 3)) = 13.5 -> 14.
    edge = _edge()
    assert edge_weight(edge).quantize(Decimal("0.000001")) == Decimal("0.436702")
    row = score_at([edge], 5)
    assert row["vouch_score"] == 14 and row["total_weight"] == "0.436702"


def test_no_endorsement_is_no_record_not_zero():
    row = score_at([_edge(created=10)], 5)
    assert row["vouch_score"] == "" and row["vouch_status"] == P.NO_RECORD


def test_reciprocal_edge_keeps_ring_penalty_of_its_quality():
    assert edge_weight(_edge(reciprocal=True)) == edge_weight(_edge()) * P.RING_PENALTY


def test_reputation_update_known_answer_and_dispute_safety():
    # delta = 0.10 * w * (y - 0.92); w = 0.436702 -> settled +0.003494.
    class B:
        borrower_id = "B1"
        app_month = 5
    settled = outcome_rows(B, [_edge()], "B1-A1", defaulted=False, settled=True, default_month="", rng=None)
    assert settled[0]["delta_reputation"] == "0.003494" and settled[0]["y"] == 1

    class Always:
        def random(self):
            return 0.0

        def choice(self, options):
            return "OPEN"
    disputed = outcome_rows(B, [_edge()], "B1-A1", defaulted=True, settled=False, default_month="2025-01", rng=Always())
    assert disputed[0]["dispute_status"] == "OPEN" and disputed[0]["delta_reputation"] == "0.000000"


def test_trajectory_from_real_grid_known_answer():
    grid = ["---"] * 20 + ["000", "030", "060", "000"]
    rows = trajectory_rows("H1", "2025-01", [{"dpd_grid": "|".join(grid), "opened_month": "2024-08"}])
    assert len(rows) == 24 and rows[-1]["snapshot_month"] == "2024-12"
    assert [r["worst_dpd_reported"] for r in rows[-4:]] == [0, 30, 60, 0]
    assert rows[-2]["months_30plus_rolling"] == 2 and rows[-1]["score_status"] == "NO_SCORE_AVAILABLE"


@pytest.fixture(scope="module")
def small(tmp_path_factory):
    out = tmp_path_factory.mktemp("shock")
    generate(30, out, 0, study=60)

    def table(name):
        with (out / f"{name}.csv").open(encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    return out, table


def test_gate1_every_bureau_shock_is_a_real_explained_drop(small):
    _, table = small
    events = table("bureau_events")
    shocks = [s for s in table("shock_events") if s["bureau_shock"] == "1"]
    assert shocks, "the study cohort should produce bureau shocks"
    for s in shocks:
        assert int(s["bureau_drop_points"]) <= P.SHOCK_DROP_POINTS
        assert any(e["borrower_id"] == s["borrower_id"] and s["shock_month"] <= e["event_month"] <= s["drop_month"]
                   and int(e["magnitude_points"]) < 0 for e in events)


def test_gate7_no_banned_column_reaches_a_model(small):
    _, table = small
    assert not set(B1_NUMERIC + B1_CATEGORICAL) & BANNED
    assert not set(table("features")[0]) & BANNED


def test_features_read_only_pre_application_vouch_state(small):
    _, table = small
    last = {}
    for r in table("vouch_scores"):
        last[r["borrower_id"]] = r      # rows are oldest first; the last is the month before applying
    for f in table("features"):
        assert f["vouch_score"] == last[f["borrower_id"]]["vouch_score"]


def test_gate8_reason_codes_cite_bureau_events(small):
    _, table = small
    by_borrower = {}
    for e in table("bureau_events"):
        by_borrower.setdefault(e["borrower_id"], []).append(e)
    cited = total = 0
    for s in table("bureau_snapshots"):
        if s["top_reason_codes"] and s["score_change_3m"] and int(s["score_change_3m"]) < 0:
            codes = {e["reason_code"] for e in by_borrower.get(s["borrower_id"], []) if e["event_month"] <= s["snapshot_month"]}
            for code in s["top_reason_codes"].split("|"):
                total += 1
                cited += code in codes
    assert total and cited / total >= 0.9


def test_gate9_no_voucher_is_over_budget_and_rings_score_low(small):
    _, table = small
    staked, budget = {}, {}
    for e in table("vouch_events"):
        if e["action"] == "CREATED":
            staked[e["voucher_id"]] = staked.get(e["voucher_id"], 0) + float(e["commitment_points"])
            budget[e["voucher_id"]] = float(e["voucher_budget_points"])
            assert 0 <= float(e["utilisation_at_stake"]) <= 1
    assert all(staked[v] <= budget[v] or budget[v] == 0 for v in staked)
    ring_only = [int(r["vouch_score"]) for r in table("vouch_scores")
                 if r["vouch_score"] and r["reciprocal_edges"] != "0" and r["reciprocal_edges"] == r["eligible_incoming"]]
    assert max(ring_only, default=0) <= 10


def test_gate10_two_runs_are_byte_identical(small, tmp_path):
    out, _ = small
    generate(30, tmp_path, 0, study=60)
    first = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["files"]
    second = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["files"]
    assert {k: v["sha256"] for k, v in first.items()} == {k: v["sha256"] for k, v in second.items()}


def test_gate12_disputes_never_move_reputation(small):
    _, table = small
    for r in table("vouch_outcomes"):
        if r["dispute_status"] in ("OPEN", "UPHELD") or r["y"] == "":
            assert Decimal(r["delta_reputation"]) == 0


def test_sample_weights_only_on_the_main_cohort(small):
    _, table = small
    for f in table("features"):
        assert (f["sample_weight"] == "") == (f["cohort"] == "shock_study")


def test_prosper_build_keeps_no_keys_and_labels_resolved_loans(tmp_path):
    raw = tmp_path / "raw" / "prosper"
    raw.mkdir(parents=True)
    columns = ["ListingKey", "MemberKey", "LoanStatus", "Recommendations", "InvestmentFromFriendsCount",
               "InvestmentFromFriendsAmount", "ScorexChangeAtTimeOfListing", "ListingCreationDate", "Term",
               "LoanOriginalAmount", "CreditScoreRangeLower", "CreditScoreRangeUpper", "CurrentDelinquencies",
               "DelinquenciesLast7Years", "BankcardUtilization", "DebtToIncomeRatio", "StatedMonthlyIncome",
               "IncomeVerifiable", "EmploymentStatus", "TotalProsperLoans", "OnTimeProsperPayments", "CurrentlyInGroup"]
    fake = [  # invented rows, not Prosper data
        ["K1", "M1", "Completed", "1", "0", "0", "-60", "2008-01-02 10:00:00", "36", "1000.50", "640", "659", "0", "0",
         "0.5", "0.2", "3000", "True", "Employed", "1", "10", "False"],
        ["K2", "M2", "Chargedoff", "0", "0", "0", "", "2008-02-02 10:00:00", "36", "2000", "600", "619", "1", "2",
         "0.9", "0.4", "2500", "False", "Employed", "", "", "False"],
        ["K3", "M3", "Current", "0", "0", "0", "", "2013-02-02 10:00:00", "36", "2000", "700", "719", "0", "0",
         "0.1", "0.1", "5000", "True", "Employed", "", "", "False"],
    ]
    with (raw / "prosperLoanData.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(fake)
    build_prosper(tmp_path / "raw", tmp_path / "out")
    with (tmp_path / "out" / "prosper_loans.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert "ListingKey" not in rows[0] and "MemberKey" not in rows[0]
    assert rows[0]["loan_amount_minor"] == "100050" and rows[0]["currency"] == "USD"
    assert [r["bad"] for r in rows] == ["0", "1", ""] and rows[0]["endorsed"] == "1"
    assert check_prosper(rows)["resolved_loans"] == 2


def test_every_borrower_has_conditions_and_valid_life_events(small):
    _, table = small
    assert {r["conditions"] for r in table("truth")} <= {"NORMAL", "IDIOSYNCRATIC", "COVARIATE", "BOTH"}
    assert {r["category"] for r in table("life_events")} <= {"IDIOSYNCRATIC", "COVARIATE", "NOISE"}
