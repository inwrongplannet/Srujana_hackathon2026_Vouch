"""The gates the shock question must pass before anyone may claim an answer.

python -m veritrust.synth.shock_validate [--data ../data/synth] [--prosper ../data/prosper]

Question: when a borrower's bureau score falls after a shock but their vouch score holds, is
post-shock default lower, holding the pre-shock score band and shock severity fixed?
Each gate prints PASS or FAIL with its number; results also go to shock_validation.json in --data.
A FAIL means the claim it guards must not be made. Stdlib only, like validate.py.
"""

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from . import params as P
from .bureau import band
from .validate import auc, encode, logistic, predict, read, standardise

# B0: what a conventional lender sees (bureau plus cash flow); B1 adds the shock as reported by the
# applicant and the vouch graph. Vouch-held, outcomes, support received and the truth table are
# banned from both (gate 7).
B0_NUMERIC = [
    "requested_amount_minor", "tenure_months", "rate_annual", "new_emi_minor", "declared_income_minor",
    "declared_emi_minor", "occupation_tenure_months", "bank_statement_months", "income_est_minor",
    "existing_emi_est_minor", "dti_est", "amount_to_income", "bank_income_median_minor", "bank_income_cv",
    "bank_bounces", "bank_bounces_3m", "bank_low_balance_months", "bank_surplus_median_minor",
    "bureau_tradelines", "bureau_active", "bureau_history_months", "bureau_max_dpd_24m",
    "bureau_months_30plus_24m", "bureau_new_6m", "bureau_written_off", "bureau_emi_minor",
    "bureau_score", "bureau_score_change_3m", "bureau_score_change_6m", "bureau_worst_change_3m_6m",
    "bureau_utilisation", "bureau_enquiries_6m_at_app", "bureau_events_3m", "dependents", "urban",
]
B0_CATEGORICAL = ["occupation", "age_band", "product", "bank_statement_status", "bureau_score_status",
                  "bureau_top_reason_code"]
SHOCK_NUMERIC = B0_NUMERIC + ["shock_reported_severity", "shock_reported_insured"]
SHOCK_CATEGORICAL = B0_CATEGORICAL + ["shock_reported_status", "shock_reported_type"]
B1_NUMERIC = SHOCK_NUMERIC + [
    "vouch_score", "vouch_score_change_6m",
    "vouch_eligible_incoming", "vouch_total_weight", "vouch_distinct_anchors", "vouch_max_contributor_share",
    "vouch_reciprocal_edges", "vouch_cluster_concentration", "vouch_mean_reliability", "vouch_withdrawn_6m",
]
B1_CATEGORICAL = SHOCK_CATEGORICAL + ["vouch_score_status"]
VOUCH_BLOCK = [c for c in B1_NUMERIC if c.startswith("vouch_")] + ["vouch_score_status"]
BANNED = {"vouch_held", "delta_reputation", "y", "default_driver", "support_mobilised_minor",
          "support_before_application_minor", "perf_vouch_support_minor", "support_capacity", "discipline",
          "shock_planned", "default_12m", "default_month", "max_dpd_12m", "paid_minor", "dpd_days",
          "world_id", "world_pandemic_onset", "pandemic_path", "irrigated", "months_out_of_work",
          "covariate_events", "noise_events", "conditions"}


def _rate(rows: list[dict]) -> float:
    return sum(int(r["default_12m"]) for r in rows) / len(rows) if rows else float("nan")


def stratified_difference(rows: list[dict], treated, strata) -> float:
    """Mantel-Haenszel-style risk difference: per-stratum gaps weighted by n1*n0/(n1+n0)."""
    groups: dict = defaultdict(lambda: ([], []))
    for r in rows:
        groups[strata(r)][0 if treated(r) else 1].append(int(r["default_12m"]))
    num = den = 0.0
    for t, c in groups.values():
        if t and c:
            w = len(t) * len(c) / (len(t) + len(c))
            num += w * (sum(t) / len(t) - sum(c) / len(c))
            den += w
    return num / den if den else float("nan")


def bootstrap_ci(rows: list[dict], stat, boots: int = 1000, seed: int = 11) -> tuple[float, float]:
    rng = random.Random(seed)
    values = sorted(stat([rows[rng.randrange(len(rows))] for _ in rows]) for _ in range(boots))
    return values[int(0.025 * boots)], values[int(0.975 * boots) - 1]


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float("nan")


def cv_predictions(rows: list[dict], numeric: list[str], categorical: list[str], folds: int = 5) -> list[float]:
    """Out-of-fold probabilities from the plain logistic model, folds by borrower id."""
    x, _ = encode(rows, numeric, categorical)
    y = [int(r["default_12m"]) for r in rows]
    fold = [int(r["borrower_id"][1:]) % folds for r in rows]
    out = [0.0] * len(rows)
    for k in range(folds):
        train = [list(x[i]) for i in range(len(rows)) if fold[i] != k]
        test_index = [i for i in range(len(rows)) if fold[i] == k]
        test = [list(x[i]) for i in test_index]
        standardise(train, test)
        w = logistic(train, [y[i] for i in range(len(rows)) if fold[i] != k])
        for i, p in zip(test_index, predict(w, test)):
            out[i] = p
    return out


def paired_delta_ci(p0: list[float], p1: list[float], y: list[int], boots: int = 400, seed: int = 5):
    rng = random.Random(seed)
    deltas = []
    for _ in range(boots):
        idx = [rng.randrange(len(y)) for _ in y]
        yy = [y[i] for i in idx]
        deltas.append(auc([p1[i] for i in idx], yy) - auc([p0[i] for i in idx], yy))
    deltas.sort()
    return deltas[int(0.025 * boots)], deltas[int(0.975 * boots) - 1]


def run(data: Path) -> dict:
    features = read(data / "features.csv")
    feature_columns = set(features[0])
    outcomes = {r["borrower_id"]: r for r in read(data / "outcomes.csv")}
    shocks = read(data / "shock_events.csv")
    for r in features:
        r["default_12m"] = outcomes[r["borrower_id"]]["default_12m"]
    for s in shocks:
        s["default_12m"] = outcomes[s["borrower_id"]]["default_12m"]
    gates: dict[str, dict] = {}

    # Gate 1: the shock definition is real and explained.
    bs = [s for s in shocks if s["bureau_shock"] == "1"]
    events = defaultdict(list)
    for e in read(data / "bureau_events.csv"):
        events[e["borrower_id"]].append(e)
    explained = sum(1 for s in bs if any(e["event_month"] <= s["drop_month"] and e["event_month"] >= s["shock_month"]
                                         and int(e["magnitude_points"]) < 0 for e in events[s["borrower_id"]]))
    big = sum(1 for s in bs if int(s["bureau_drop_points"]) <= P.SHOCK_DROP_POINTS)
    gates["1_shock_definition"] = {"bureau_shocks": len(bs), "shocked": len(shocks),
                                   "share_drop_le_minus50": big / len(bs), "share_explained_by_event": explained / len(bs),
                                   "pass": big / len(bs) >= 0.95 and explained == len(bs)}

    # Gate 2: bureau and vouch carry different information before the shock.
    both = [s for s in bs if s["pre_vouch_score"] != "" and s["pre_bureau_score"] != ""]
    corr = pearson([float(s["pre_bureau_score"]) for s in both], [float(s["pre_vouch_score"]) for s in both])
    gates["2_orthogonality"] = {"n": len(both), "corr": corr, "pass": abs(corr) < 0.5}

    # Gate 3: conditional association, held vs not held, within pre-score band x severity.
    def strata(r):
        return band(int(r["pre_bureau_score"])), r["severity"]

    def held(r):
        return r["vouch_held"] == "1"

    diff = stratified_difference(bs, held, strata)
    low, high = bootstrap_ci(bs, lambda rows: stratified_difference(rows, held, strata))
    vouched = [s for s in bs if s["pre_vouch_score"] != ""]
    diff_vouched = stratified_difference(vouched, held, strata)
    gates["3_conditional_association"] = {
        "held_n": sum(1 for s in bs if held(s)), "not_held_n": sum(1 for s in bs if not held(s)),
        "default_held": _rate([s for s in bs if held(s)]), "default_not_held": _rate([s for s in bs if not held(s)]),
        "stratified_difference": diff, "ci95": [low, high],
        "stratified_difference_among_vouched": diff_vouched,
        "pass": diff <= -0.04 and high < 0}

    # Gate 4: dose-response across vouch-score quartiles among bureau shocks with a vouch score.
    scored = sorted((s for s in bs if s["post_vouch_score"] != ""), key=lambda s: int(s["post_vouch_score"]))
    quarters = [scored[k * len(scored) // 4:(k + 1) * len(scored) // 4] for k in range(4)]
    rates = [_rate(q) for q in quarters]
    gates["4_dose_response"] = {"no_vouch": _rate([s for s in bs if s["post_vouch_score"] == ""]),
                                "quartile_rates": rates, "quartile_floor": [int(q[0]["post_vouch_score"]) for q in quarters],
                                "pass": all(a >= b for a, b in zip(rates, rates[1:]))}

    # Gates 5, 6 and 11: 5-fold CV over every simulated row, paired on identical rows. B0 is the
    # conventional lender, BS adds the shock as the applicant reports it, B1 adds the vouch graph.
    # The vouch claim is B1 against BS, so the reported shock is not credited to the vouch.
    y = [int(r["default_12m"]) for r in features]
    p0 = cv_predictions(features, B0_NUMERIC, B0_CATEGORICAL)
    ps = cv_predictions(features, SHOCK_NUMERIC, SHOCK_CATEGORICAL)
    p1 = cv_predictions(features, B1_NUMERIC, B1_CATEGORICAL)
    delta = auc(p1, y) - auc(ps, y)
    lo, hi = paired_delta_ci(ps, p1, y)
    ids = {s["borrower_id"] for s in bs}
    sub = [i for i, r in enumerate(features) if r["borrower_id"] in ids]
    ys = [y[i] for i in sub]
    delta_shocked = auc([p1[i] for i in sub], ys) - auc([ps[i] for i in sub], ys)
    gates["5_model_increment"] = {"auc_b0": auc(p0, y), "auc_bureau_plus_shock": auc(ps, y), "auc_b1": auc(p1, y),
                                  "vouch_delta": delta, "ci95": [lo, hi], "vouch_delta_bureau_shocked": delta_shocked,
                                  "pass": delta >= 0.02 and lo > 0}

    rng = random.Random(23)
    shuffled = [dict(r) for r in features]
    donors = list(range(len(features)))
    rng.shuffle(donors)
    for r, d in zip(shuffled, donors):
        for c in VOUCH_BLOCK:
            r[c] = features[d][c]
    pp = cv_predictions(shuffled, B1_NUMERIC, B1_CATEGORICAL)
    placebo = auc(pp, y) - auc(ps, y)
    gates["6_placebo"] = {"delta_with_vouch_shuffled": placebo, "pass": abs(placebo) < 0.005}

    pairs = sorted((p1[i], y[i]) for i in sub)
    gaps = []
    for k in range(10):
        chunk = pairs[k * len(pairs) // 10:(k + 1) * len(pairs) // 10]
        gaps.append(sum(p for p, _ in chunk) / len(chunk) - sum(t for _, t in chunk) / len(chunk))
    gates["11_calibration_bureau_shocked"] = {"decile_gaps": gaps, "max_abs_gap": max(abs(g) for g in gaps),
                                              "pass": max(abs(g) for g in gaps) <= 0.02}

    # Gate 7: no banned column reaches a model.
    used = set(B1_NUMERIC + B1_CATEGORICAL)
    gates["7_leakage"] = {"banned_in_models": sorted(used & BANNED),
                          "banned_in_features_table": sorted(feature_columns & BANNED),
                          "pass": not (used & BANNED) and not (feature_columns & BANNED)}

    # Gate 8: every reason code on a falling score cites a bureau event of that reason.
    cited = total = 0
    for snap in read(data / "bureau_snapshots.csv"):
        if not snap["top_reason_codes"] or snap["score_change_3m"] == "" or int(snap["score_change_3m"]) >= 0:
            continue
        m = snap["snapshot_month"]
        y4, m2 = int(m[:4]), int(m[5:])
        start = f"{(y4 * 12 + m2 - 3) // 12:04d}-{(y4 * 12 + m2 - 3) % 12 + 1:02d}"
        found = {e["reason_code"] for e in events[snap["borrower_id"]] if start <= e["event_month"] <= m}
        for code in snap["top_reason_codes"].split("|"):
            total += 1
            cited += code in found
    gates["8_explanation_grounding"] = {"codes": total, "share_cited": cited / total if total else 1.0,
                                        "pass": total == 0 or cited / total >= 0.9}

    # Gate 9: graph invariants. Stakes never exceed a voucher's budget; U in [0, 1]; a ring adds little.
    staked: dict[str, float] = defaultdict(float)
    budget: dict[str, float] = {}
    bad_u = 0
    for e in read(data / "vouch_events.csv"):
        if e["action"] == "CREATED" and e["voucher_kind"] and e["voucher_budget_points"]:
            staked[e["voucher_id"]] += float(e["commitment_points"])
            budget[e["voucher_id"]] = float(e["voucher_budget_points"])
            bad_u += not 0 <= float(e["utilisation_at_stake"]) <= 1
    over = sum(1 for v, s in staked.items() if s > budget[v] + 1e-9)
    ring_only = [int(r["vouch_score"]) for r in read(data / "vouch_scores.csv")
                 if r["vouch_score"] != "" and r["reciprocal_edges"] != "0" and r["reciprocal_edges"] == r["eligible_incoming"]]
    gates["9_graph_invariants"] = {"vouchers_over_budget": over, "edges_with_bad_utilisation": bad_u,
                                   "ring_only_rows": len(ring_only), "ring_only_max_score": max(ring_only, default=0),
                                   "pass": over == 0 and bad_u == 0 and max(ring_only, default=0) <= 10}

    # Gate 10: determinism is checked by the test suite (two runs, identical bytes); record hashes here.
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    gates["10_determinism"] = {"sha256": {k: v["sha256"][:16] for k, v in manifest["files"].items()},
                               "pass": True, "note": "tests/test_shock_data.py regenerates and compares"}

    # Scenario report (not a gate): default by what borrowers lived through, with and without an
    # established vouch, and the held-vouch gap for bureau shocks by kind of conditions.
    truth = {r["borrower_id"]: r for r in read(data / "truth.csv")}
    scenarios = {}
    for label in ("NORMAL", "IDIOSYNCRATIC", "COVARIATE", "BOTH"):
        group = [r for r in features if truth[r["borrower_id"]]["conditions"] == label]
        est = [r for r in group if r["vouch_score_status"] == "ESTABLISHED"]
        none = [r for r in group if r["vouch_score_status"] == "NO_RECORD"]
        scenarios[label] = {"n": len(group), "default": _rate(group), "established_vouch": _rate(est),
                            "no_vouch": _rate(none), "gap": _rate(none) - _rate(est) if est and none else None}
        shocked = [s for s in bs if truth[s["borrower_id"]]["conditions"] == label]
        if shocked and any(held(s) for s in shocked) and any(not held(s) for s in shocked):
            scenarios[label]["bureau_shock_held_minus_not"] = _rate([s for s in shocked if held(s)]) - _rate([s for s in shocked if not held(s)])
    gates["scenarios"] = {**scenarios, "pass": True, "note": "report only"}

    # Gate 12: an open or overturned dispute never moves reputation.
    unsafe = [r for r in read(data / "vouch_outcomes.csv")
              if r["dispute_status"] in ("OPEN", "UPHELD") and float(r["delta_reputation"]) != 0]
    gates["12_reputation_safety"] = {"violations": len(unsafe), "pass": not unsafe}
    return gates


def main() -> None:
    parser = argparse.ArgumentParser(description="Validation gates for the shock question.")
    parser.add_argument("--data", type=Path, default=Path("../data/synth"))
    args = parser.parse_args()
    gates = run(args.data)
    for name, result in gates.items():
        detail = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in result.items() if k != "pass"}
        print(f"{'PASS' if result['pass'] else 'FAIL'}  {name}  {detail}")
    (args.data / "shock_validation.json").write_text(json.dumps(gates, indent=2, default=str) + "\n",
                                                     encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
