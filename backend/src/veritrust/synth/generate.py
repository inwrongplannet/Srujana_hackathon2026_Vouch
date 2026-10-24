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

from . import params as P
from .features import build_features
from .model import Loan, month_label
from .money import emi, principal_for_emi, round_to, rupees, scale
from .observe import (bank_view, bureau_view, declared_view, existing_emi_true, gst_view,
                      statement_months, vouch_view)
from .people import lognormal, pick, sample_borrower
from .simulate import simulate
from .transactions import to_transactions

TABLES = ("applications", "monthly_cashflow", "bureau_tradelines", "gst_filings", "vouches",
          "outcomes", "truth", "features", "transactions")


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
    macro = (b.macro_exposed and months & (P.RAINFALL_DEFICIT["crop_months"] | P.RAINFALL_DEFICIT["wage_months"])) \
        or (b.segment == "gig_platform" and months & P.GIG_INCENTIVE_CUT["months"])
    if any(m.shock for m in performance) or macro:
        return "SHOCK"
    if b.stacker:
        return "STACKING"
    return "LIQUIDITY"


def generate_one(index: int, with_transactions: bool) -> dict[str, list[dict]]:
    """All rows for one borrower, keyed by table name."""
    rng = random.Random(f"{P.SEED}:{index}")
    b = sample_borrower(index, rng)
    initial_income = b.base_income
    new = _application_loan(b, rng)
    history, performance = simulate(b, rng, new)

    app_label = month_label(b.app_month)
    months, statement_status = statement_months(b, rng)
    declared = declared_view(b, history, rng)
    bank = bank_view(b, history, months, rng) if months else []
    tradelines = bureau_view(b, b.app_month, rng)
    gst = gst_view(b, history, rng)
    vouches = vouch_view(b, rng)

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

    recent = [t.income for t in history[-P.STATEMENT_MONTHS:]]
    true_income = int(median(recent))
    existing = existing_emi_true(b)
    true_dti = (Decimal(existing + new.emi) / Decimal(true_income)) if true_income else Decimal("9.9999")
    undeclared = [loan for loan in b.loans
                  if not loan.is_new and not loan.declared and not loan.written_off and loan.is_open(b.app_month - 1)]
    truth = {
        "borrower_id": b.borrower_id, "base_income_minor": initial_income, "true_income_median_12m_minor": true_income,
        "income_cv": f"{b.cv:.4f}", "expense_ratio": f"{b.expense_ratio:.4f}", "discipline": f"{b.discipline:.4f}",
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
        "default_driver": _default_driver(b, outcome, performance, true_dti),
    }

    rows = {
        "applications": [app], "monthly_cashflow": monthly,
        "bureau_tradelines": [{"borrower_id": b.borrower_id, **t} for t in tradelines],
        "gst_filings": [{"borrower_id": b.borrower_id, **g} for g in gst],
        "vouches": [{"borrower_id": b.borrower_id, **v} for v in vouches],
        "outcomes": [outcome], "truth": [truth], "features": [features], "transactions": [],
    }
    if with_transactions and bank:
        loans = {loan.loan_id: loan for loan in b.loans}
        counter = [0]
        tx_rng = random.Random(f"{P.SEED}:{index}:txn")
        for bm in bank:
            rows["transactions"].extend(to_transactions(b, bm, loans, tx_rng, counter))
    return rows


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


def generate(n: int, out: Path, transaction_sample: int) -> dict:
    """Generate `n` borrowers into `out`; line-level statements for the first `transaction_sample`."""
    out.mkdir(parents=True, exist_ok=True)
    tables: dict[str, list[dict]] = {name: [] for name in TABLES}
    for index in range(1, n + 1):
        for name, rows in generate_one(index, index <= transaction_sample).items():
            tables[name].extend(rows)
    files = {}
    for name in TABLES:
        path = out / f"{name}.csv"
        write_csv(path, tables[name])
        files[f"{name}.csv"] = {"rows": len(tables[name]),
                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {
        "generator_version": P.GENERATOR_VERSION, "seed": P.SEED, "borrowers": n,
        "transaction_sample": min(n, transaction_sample), "currency": P.CURRENCY,
        "money_unit": "integer paise (minor units)", "label": "default_12m = 90+ days past due within 12 EMIs",
        "notice": "Synthetic, illustrative data. Not real people, not financial advice.",
        "files": files,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8", newline="\n")
    return manifest
