"""Orchestrates the stages and writes the dataset as CSV files plus a manifest.

Determinism: every borrower gets its own RNG seeded from (SEED, index), so borrower B000042 is
identical whether you generate 500 or 20,000 people, and two runs produce byte-identical files.
"""

import csv
import hashlib
import json
import random
from decimal import Decimal
from pathlib import Path
from statistics import median

from . import bureau
from . import params as P
from .behaviour import NOISE, public_events, sample_traits
from .features import build_features, shock_vouch_features
from .model import Loan, month_label
from .money import emi, principal_for_emi, round_to, rupees, scale
from .observe import (
    bank_view,
    bureau_view,
    declared_view,
    existing_emi_true,
    gst_view,
    statement_months,
)
from .people import lognormal, pick, sample_borrower
from .shocks import plan_shock, stratum
from .simulate import simulate_group
from .transactions import to_transactions
from .vouch import (
    VoucherPool,
    event_rows,
    outcome_rows,
    plan_vouches,
    score_at,
    weight_by_month,
)
from .world import World, build_worlds, world_index

TABLES = ("applications", "monthly_cashflow", "bureau_tradelines", "gst_filings", "vouches",
          "outcomes", "truth", "features", "transactions", "bureau_snapshots", "bureau_events",
          "vouch_events", "vouch_scores", "vouch_outcomes", "loan_performance", "shock_events", "life_events")


def _application_loan(b, rng: random.Random) -> Loan:
    product = pick(rng, P.SEGMENTS[b.segment]["products"])
    rate, tenures, (share, sd) = P.PRODUCTS[product]
    rate = rate + Decimal(rng.randint(-4, 8)) * Decimal("0.005")
    tenure = rng.choice(tenures)
    target_emi = scale(b.base_income, lognormal(rng, share, sd))
    principal = round_to(principal_for_emi(target_emi, rate, tenure), rupees(1000))
    return Loan(loan_id=f"{b.borrower_id}-NEW", kind=product, lender_type="APPLIED",
                lender="APPLIED LOAN", principal=principal, rate=rate, tenure=tenure,
                emi=emi(principal, rate, tenure), start=b.app_month, emi_day=5, reported=True,
                declared=True, is_new=True)


def _outcome(b, new: Loan) -> dict:
    window = range(b.app_month + 1, b.app_month + P.PERFORMANCE_MONTHS + 1)
    dpd = [new.grid.get(m, 0) for m in window]
    first = next((m for m in window if new.grid.get(m, 0) >= P.DEFAULT_ARREARS * 30), None)
    return {
        "borrower_id": b.borrower_id, "default_12m": int(first is not None),
        "default_month": month_label(first) if first is not None else "",
        "max_dpd_12m": max(dpd) if dpd else 0,
    }


def _default_driver(b, outcome: dict, performance, true_dti: Decimal) -> str:
    if not outcome["default_12m"]:
        return ""
    if true_dti > Decimal("0.6"):
        return "STRUCTURAL"
    months = {(m.month // 12, m.month % 12 + 1) for m in performance}
    macro = any(cat == "COVARIATE" for m in performance for cat, _ in m.events) \
        or (b.segment == "gig_platform" and months & P.GIG_INCENTIVE_CUT["months"])
    if any(m.shock for m in performance) or macro:
        return "SHOCK"
    if b.stacker:
        return "STACKING"
    return "LIQUIDITY"


def _sample_weight(shocked: bool, group: str, world: World) -> str:
    """Reweights to the real population: the oversampled shocked group back to SHOCK_REAL_INCIDENCE
    within its stratum, times the world's weight back to the real pandemic chance."""
    real, share = Decimal(repr(P.SHOCK_REAL_INCIDENCE)), Decimal(repr(P.SHOCK_SHARE[group]))
    weight = real / share if shocked else (1 - real) / (1 - share)
    return str((weight * Decimal(repr(world.weight))).quantize(Decimal("0.000001")))


def _loan_performance(b, new: Loan, performance, application_id: str) -> list[dict]:
    """The applied-for loan month by month: due, paid, days past due, and help received."""
    by_month = {t.month: t for t in performance}
    rows = []
    for k in range(1, P.PERFORMANCE_MONTHS + 1):
        m = b.app_month + k
        t = by_month[m]
        due = new.emi if new.is_due(m) else 0
        paid = sum(p.amount for p in t.payments if p.loan_id == new.loan_id)
        dpd = new.grid.get(m, 0)
        if new.written_off_month is not None and new.written_off_month <= m:
            status = "CHARGED_OFF"
        elif new.dues_by(m) >= new.tenure and dpd == 0:
            status = "SETTLED"
        elif dpd == 0:
            status = "ON_TIME"
        elif paid:
            status = "LATE"
        else:
            status = "MISSED"
        rows.append({
            "application_id": application_id, "borrower_id": b.borrower_id, "month": k,
            "calendar_month": month_label(m), "due_minor": due, "paid_minor": paid, "dpd_days": dpd,
            "status": status, "shock_active": int(bool(t.shock or t.lumpy)),
            "support_received_minor": t.informal_support + t.vouch_support,
            "vouch_support_minor": t.vouch_support,
        })
    return rows


def _shock_row(b, group: str, snaps: list[dict], vouch_rows: list[dict], events: list[dict], history,
               performance) -> dict:
    """The shock under analysis: when the bureau score fell, by how much, and what the vouch did."""
    plan = b.shock
    score = {r["snapshot_month"]: r["bureau_score"] for r in snaps}
    vouch = {r["snapshot_month"]: r["vouch_score"] for r in vouch_rows}
    # Pre-shock = the month before the shock; the drop is the lowest score in the next
    # SHOCK_DROP_WINDOW months (all before the application), relative to that.
    pre_label = month_label(plan.start - 1)
    before = score.get(pre_label, "")
    drop_month, drop = None, None
    for m in range(plan.start, min(plan.start + P.SHOCK_DROP_WINDOW, b.app_month)):
        now = score.get(month_label(m), "")
        if now != "" and before != "" and (drop is None or now - before < drop):
            drop_month, drop = m, now - before
    post_label = month_label(drop_month) if drop_month is not None else month_label(b.app_month - 1)
    window = {month_label(m) for m in range(plan.start, plan.start + P.SHOCK_DROP_WINDOW)}
    explained = any(e["event_month"] in window and e["magnitude_points"] < 0 for e in events)
    pre_v, post_v = vouch.get(pre_label, ""), vouch.get(post_label, "")
    held = pre_v != "" and post_v != "" and post_v >= pre_v - P.VOUCH_HELD_SLACK and post_v >= P.VOUCH_HELD_FLOOR
    support_pre = sum(t.vouch_support for t in history if t.month >= plan.start)
    support_post = sum(t.vouch_support for t in performance)
    return {
        "shock_id": f"{b.borrower_id}-S1", "borrower_id": b.borrower_id, "shock_month": month_label(plan.start),
        "stratum": group,
        "shock_type": plan.kind, "severity": plan.severity, "insured": int(plan.insured),
        "expense_minor": plan.expense, "income_factor": f"{plan.income_factor:.2f}", "shock_months": plan.months,
        "drop_month": month_label(drop_month) if drop_month is not None else "",
        "pre_bureau_score": before if drop_month is not None else "",
        "post_bureau_score": score.get(post_label, "") if drop_month is not None else "",
        "bureau_score_at_application": score.get(month_label(b.app_month - 1), ""),
        "bureau_drop_points": drop if drop is not None else "",
        "bureau_shock": int(drop is not None and drop <= P.SHOCK_DROP_POINTS and explained),
        "pre_vouch_score": pre_v, "post_vouch_score": post_v, "vouch_held": int(held),
        "support_mobilised_minor": support_pre + support_post,
        "support_before_application_minor": support_pre,
    }


def _study_borrower(index: int):
    """A shock-study borrower: redraw (deterministically) until they carry live reported credit."""
    for attempt in range(P.STUDY_MAX_DRAWS):
        rng = random.Random(f"{P.SEED}:{index}:study:{attempt}")
        b = sample_borrower(index, rng)
        if stratum(b) == "active_credit":
            return b, rng
    raise RuntimeError(f"no borrower with live credit after {P.STUDY_MAX_DRAWS} draws for {index}")


def _conditions(b, history, performance) -> tuple[str, list[dict]]:
    """Label what the borrower lived through around the loan, and list every logged event.

    NORMAL: nothing unusual in the last 6 months before applying or during the loan.
    IDIOSYNCRATIC: a personal emergency (medical, job loss, family, crop, business).
    COVARIATE: a regional event that hit many people at once. BOTH: one of each.
    NOISE events (theft, unexplained costs, failed debits) are logged but do not set the label.
    """
    window = history[-6:] + performance
    personal = any(t.shock for t in window) or (b.shock is not None and b.shock.start >= b.app_month - 6)
    regional = any(cat == "COVARIATE" for t in window for cat, _ in t.events)
    label = "BOTH" if personal and regional else "IDIOSYNCRATIC" if personal else "COVARIATE" if regional else "NORMAL"
    rows = []
    for t in history + performance:
        for cat, name in t.events:
            rows.append({"borrower_id": b.borrower_id, "month": month_label(t.month), "category": cat, "event": name,
                         "phase": "history" if t.month < b.app_month else "loan"})
        if t.shock:
            rows.append({"borrower_id": b.borrower_id, "month": month_label(t.month), "category": "IDIOSYNCRATIC",
                         "event": t.shock.upper(), "phase": "history" if t.month < b.app_month else "loan"})
    return label, rows


def _prepare(index: int, pool: VoucherPool, cohort: str, worlds: list[World]) -> dict:
    """Everything decided before the months are lived: the person, their loan, shock, vouches and
    world. Runs in index order, because endorsers' staked points are a ledger across borrowers."""
    if cohort == "shock_study":
        b, rng = _study_borrower(index)
    else:
        rng = random.Random(f"{P.SEED}:{index}")
        b = sample_borrower(index, rng)
    prep = {"index": index, "cohort": cohort, "b": b, "rng": rng, "initial_income": b.base_income}
    prep["new"] = _application_loan(b, rng)
    prep["group"] = stratum(b)
    b.shock = plan_shock(b, random.Random(f"{P.SEED}:{index}:shock"), force=cohort == "shock_study")
    prep["received"], prep["given"] = plan_vouches(b, pool, random.Random(f"{P.SEED}:{index}:vouch"))
    b.vouch_weight = weight_by_month(
        prep["received"], range(b.app_month - P.HISTORY_MONTHS, b.app_month + P.PERFORMANCE_MONTHS + 1))
    world = worlds[world_index(index)]
    b.traits = sample_traits(b, world, random.Random(f"{P.SEED}:{index}:traits"))
    prep["discipline_start"] = b.discipline
    prep["aux"] = random.Random(f"{P.SEED}:{index}:aux")
    return prep


def generate_one(index: int, with_transactions: bool, pool: VoucherPool | None = None,
                 cohort: str = "main", worlds: list[World] | None = None) -> dict[str, list[dict]]:
    """All rows for one borrower simulated alone (a neighbourhood group of one), keyed by table.

    `pool` holds the endorsers shared across borrowers (their staked points are a ledger); a
    standalone call gets a fresh pool. `cohort` is "main" (the population) or "shock_study".
    """
    prep = _prepare(index, pool or VoucherPool(), cohort, worlds or build_worlds())
    history, performance = simulate_group([(prep["b"], prep["rng"], prep["new"], prep["aux"])])[0]
    return _finish(prep, history, performance, with_transactions)


def _finish(prep: dict, history, performance, with_transactions: bool) -> dict[str, list[dict]]:
    """Turn a lived window into rows: the observed views, features, outcome and answer key."""
    index, cohort, b, rng, new = prep["index"], prep["cohort"], prep["b"], prep["rng"], prep["new"]
    group, received, given = prep["group"], prep["received"], prep["given"]
    initial_income, discipline_start = prep["initial_income"], prep["discipline_start"]
    world = b.traits.world

    app_label = month_label(b.app_month)
    months, statement_status = statement_months(b, rng)
    declared = declared_view(b, history, rng)
    bank = bank_view(b, history, months, rng) if months else []
    tradelines = bureau_view(b, b.app_month, rng)
    gst = gst_view(b, history, rng)
    vouches = [{"vouch_id": e.vouch_id, "relationship": e.relationship.lower(), "months_known": e.months_known,
                "voucher_on_time_share": f"{e.voucher.reliability:.2f}"}
               for e in received if e.active(b.app_month - 1)]

    app = {
        "borrower_id": b.borrower_id, "application_month": app_label, "occupation": b.segment,
        "state": b.state, "urban": int(b.urban), "age_band": b.age_band, "dependents": b.dependents,
        "product": new.kind, "requested_amount_minor": new.principal, "tenure_months": new.tenure,
        "rate_annual": str(new.rate), "new_emi_minor": new.emi, "currency": P.CURRENCY,
        **declared, "bank_statement_status": statement_status,
    }
    monthly = [{
        "borrower_id": b.borrower_id, "month": month_label(bm.month), "credits_minor": bm.credits(),
        "debits_minor": bm.debits(), "emi_debits_minor": sum(a for _, a, _ in bm.loan_debits),
        "emi_bounces": len(bm.returns), "bounce_charges_minor": bm.charges,
        "disbursal_credits_minor": sum(a for _, a in bm.disbursals), "disbursal_count": len(bm.disbursals),
        "opening_balance_minor": bm.opening, "closing_balance_minor": bm.closing,
    } for bm in bank]
    features = build_features(app, monthly, tradelines, gst, vouches)
    app["legacy_decision"], app["legacy_reason"] = features["legacy_decision"], features["legacy_reason"]
    outcome = _outcome(b, new)
    application_id = f"{b.borrower_id}-A1"

    snaps = bureau.snapshots(b)
    bureau_events = bureau.events(b)
    vouch_rows = [{"borrower_id": b.borrower_id, "snapshot_month": month_label(m), **score_at(received, m),
                   "algorithm_version": P.VOUCH_ALGORITHM}
                  for m in range(b.app_month - P.HISTORY_MONTHS, b.app_month)]
    vouch_events = event_rows(b, received, given)
    features.update(shock_vouch_features(b, snaps, vouch_rows, vouch_events, bureau_events,
                                         random.Random(f"{P.SEED}:{index}:report")))
    app["cohort"] = features["cohort"] = cohort
    # Public news a lender can see: disasters reported in the borrower's state lately, and how far
    # into a pandemic the country is.
    features["regional_events_6m"] = len(public_events(b, range(b.app_month - 6, b.app_month)))
    phase = world.pandemic_phase(b.app_month - 1)
    features["pandemic_months_at_app"] = "" if phase is None else phase
    conditions, life_rows = _conditions(b, history, performance)
    b.macro_exposed = conditions in ("COVARIATE", "BOTH")
    features["sample_weight"] = app["sample_weight"] = (
        _sample_weight(b.shock is not None, group, world) if cohort == "main" else "")
    features["world_weight"] = app["world_weight"] = f"{world.weight:.6f}"
    settled = (new.tenure <= P.PERFORMANCE_MONTHS and not outcome["default_12m"]
               and new.dues_by(b.app_month + P.PERFORMANCE_MONTHS) >= new.tenure)

    recent = [t.income for t in history[-P.STATEMENT_MONTHS:]]
    true_income = int(median(recent))
    existing = existing_emi_true(b)
    true_dti = (Decimal(existing + new.emi) / Decimal(true_income)) if true_income else Decimal("9.9999")
    undeclared = [loan for loan in b.loans
                  if not loan.is_new and not loan.declared and not loan.written_off and loan.is_open(b.app_month - 1)]
    truth = {
        "borrower_id": b.borrower_id, "base_income_minor": initial_income, "true_income_median_12m_minor": true_income,
        "income_cv": f"{b.cv:.4f}", "expense_ratio": f"{b.expense_ratio:.4f}", "discipline": f"{discipline_start:.4f}",
        "save_rate": f"{b.save_rate:.4f}", "deposit_share": f"{b.deposit_share:.4f}", "margin": f"{b.margin:.4f}",
        "stacker": int(b.stacker), "inflator": int(b.inflator), "window_dresser": int(b.window_dresser),
        "round_tripper": int(b.round_tripper and bool(bank)), "duplicate_import": int(b.duplicate_import and bool(bank)),
        "macro_exposed": int(b.macro_exposed), "community": int(b.community),
        "existing_emi_true_minor": existing, "undeclared_emi_minor": sum(loan.emi for loan in undeclared),
        "unreported_open_loans": sum(1 for loan in b.loans if not loan.is_new and not loan.reported
                                     and loan.is_open(b.app_month - 1)),
        "true_dti_with_new": str(true_dti.quantize(Decimal("0.0001"))),
        "perf_shocks": ";".join(sorted({m.shock for m in performance if m.shock})),
        "perf_lumpy_costs": ";".join(sorted({m.lumpy for m in performance if m.lumpy})),
        "perf_informal_support_minor": sum(m.informal_support for m in performance),
        "perf_new_digital_loans": sum(len(m.disbursals) for m in performance),
        "perf_vouch_support_minor": sum(m.vouch_support for m in performance),
        "support_capacity": f"{b.support_capacity:.4f}",
        "shock_planned": b.shock.kind if b.shock else "",
        "world_id": world.world_id,
        "world_pandemic_onset": "" if world.pandemic_onset is None else month_label(world.pandemic_onset),
        "pandemic_path": b.traits.pandemic_path if world.pandemic_onset is not None else "",
        "irrigated": int(b.traits.irrigated) if b.segment == "smallholder_farmer" else "",
        "months_out_of_work": b.traits.out_months,
        "discipline_end": f"{b.discipline:.4f}",
        "discipline_change": f"{b.discipline - discipline_start:.4f}",
        "covariate_events": sum(1 for t in history + performance for cat, _ in t.events if cat == "COVARIATE"),
        "noise_events": sum(1 for t in history + performance for cat, _ in t.events if cat == NOISE),
        "default_driver": _default_driver(b, outcome, performance, true_dti),
    }

    rows = {
        "applications": [app], "monthly_cashflow": monthly,
        "bureau_tradelines": [{"borrower_id": b.borrower_id, **t} for t in tradelines],
        "gst_filings": [{"borrower_id": b.borrower_id, **g} for g in gst],
        "vouches": [{"borrower_id": b.borrower_id, **v} for v in vouches],
        "outcomes": [outcome], "truth": [truth], "features": [features], "transactions": [],
        "bureau_snapshots": snaps, "bureau_events": bureau_events, "vouch_events": vouch_events,
        "vouch_scores": vouch_rows,
        "vouch_outcomes": outcome_rows(b, received, application_id, bool(outcome["default_12m"]), settled,
                                       outcome["default_month"], random.Random(f"{P.SEED}:{index}:dispute")),
        "loan_performance": _loan_performance(b, new, performance, application_id),
        "shock_events": [_shock_row(b, group, snaps, vouch_rows, bureau_events, history, performance)] if b.shock else [],
        "life_events": life_rows,
    }
    rows["truth"][0]["conditions"] = conditions
    if with_transactions and bank:
        loans = {loan.loan_id: loan for loan in b.loans}
        counter = [0]
        tx_rng = random.Random(f"{P.SEED}:{index}:txn")
        for bm in bank:
            rows["transactions"].extend(to_transactions(b, bm, loans, tx_rng, counter))
    return rows


def neighbourhoods(preps: list[dict]) -> list[list[dict]]:
    """Neighbourhood groups of GROUP_SIZE: same cohort, world, state and area, in index order.

    Peers share a world (one history of the country) and a place; the shock-study cohort is kept
    apart so its forced shocks never become the main population's peers.
    """
    by_key: dict[tuple, list[dict]] = {}
    for prep in preps:
        b = prep["b"]
        by_key.setdefault((prep["cohort"], b.traits.world.world_id, b.state, b.urban), []).append(prep)
    groups = []
    for key in sorted(by_key, key=str):
        members = by_key[key]
        groups += [members[i:i + P.GROUP_SIZE] for i in range(0, len(members), P.GROUP_SIZE)]
    return groups


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write rows as UTF-8 CSV with \n line endings; None becomes an empty cell."""
    if not rows:
        path.write_text("", encoding="utf-8", newline="\n")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if v is None else v) for k, v in row.items()})


def generate(n: int, out: Path, transaction_sample: int, study: int = 0) -> dict:
    """Generate `n` main borrowers and `study` shock-study borrowers into `out`.

    Line-level statements for the first `transaction_sample` main borrowers. Study ids start at
    STUDY_OFFSET + 1 and share the endorser pool with the main population.
    """
    out.mkdir(parents=True, exist_ok=True)
    tables: dict[str, list[dict]] = {name: [] for name in TABLES}
    pool = VoucherPool()
    worlds = build_worlds()
    jobs = [(i, "main") for i in range(1, n + 1)] + [(P.STUDY_OFFSET + i, "shock_study") for i in range(1, study + 1)]
    preps = [_prepare(index, pool, cohort, worlds) for index, cohort in jobs]
    lived = {}
    for members in neighbourhoods(preps):
        results = simulate_group([(m["b"], m["rng"], m["new"], m["aux"]) for m in members])
        for m, result in zip(members, results):
            lived[m["index"]] = result
    for prep in preps:
        history, performance = lived[prep["index"]]
        for name, rows in _finish(prep, history, performance, prep["index"] <= transaction_sample).items():
            tables[name].extend(rows)
    files = {}
    for name in TABLES:
        path = out / f"{name}.csv"
        write_csv(path, tables[name])
        files[f"{name}.csv"] = {"rows": len(tables[name]),
                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {
        "generator_version": P.GENERATOR_VERSION, "seed": P.SEED, "borrowers": n + study,
        "cohorts": {"main": n, "shock_study": study},
        "transaction_sample": min(n, transaction_sample), "currency": P.CURRENCY,
        "money_unit": "integer paise (minor units)", "label": "default_12m = 90+ days past due within 12 EMIs",
        "notice": "Synthetic, illustrative data. Not real people, not financial advice.",
        "files": files,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8", newline="\n")
    return manifest
