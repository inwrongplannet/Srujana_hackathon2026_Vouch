"""Build the anchored dataset: real Home Credit applicants, synthetic statements on top.

python -m veritrust.anchor.build [--n 30000] [--raw ../data/external] [--out ../data/anchored]

Real (Home Credit, never altered): who the applicant is, their income and employment, the loan
applied for, every bureau tradeline with its monthly payment grid, their instalment-level
repayment history with the lender, refused applications, their real missing values and the real
default label (TARGET: payment difficulties on the loan).
Synthetic, generated from each person's real columns and never from TARGET: a 12-month bank
statement (income from their real income, EMIs from their real annuities and instalments,
bounces placed in the months their real records show late or short payment), whether they shared
it, GST filings for businesses, the declared-EMI field, and flagged test injections (hidden loan,
window dressing, round-tripping, duplicate rows) listed in injections.csv as an answer key.
Volatility and balance buffers are drawn from real Berka accounts (berka_calibration.json).

Not carried at all: EXT_SOURCE_1..3 (opaque external scores) and protected attributes
(gender, family status, education). Money: Home Credit amounts x SCALE, as integer paise.
"""

import argparse
import hashlib
import json
import math
import random
from bisect import bisect_left
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from veritrust.synth import params as P
from veritrust.synth.features import build_features, ratio
from veritrust.synth.generate import write_csv
from veritrust.synth.model import Loan, month_label
from veritrust.synth.money import round_to, rupees, scale
from veritrust.synth.observe import BankMonth, split_income
from veritrust.synth.transactions import to_transactions

from .trajectory import trajectory_rows

SEED = 42
VERSION = "1.0.0"
# Home Credit's income and annuity are monthly-scale (median annuity/income about 0.17).
# Rescale so the median applicant earns about ₹25,000 a month; every ratio is unchanged.
SCALE = Decimal("0.17")
DAYS_PER_MONTH = Decimal("30.4375")
CALIBRATION = Path(__file__).with_name("berka_calibration.json")

INCOME_STYLE = {"Working": "transfer", "State servant": "transfer", "Maternity leave": "transfer",
                "Pensioner": "pension", "Commercial associate": "cash", "Businessman": "cash",
                "Unemployed": "cash", "Student": "cash"}
NARRATION_SEGMENT = {"transfer": "salaried_formal", "pension": "pension", "cash": "kirana_msme"}
P_LINK = {"transfer": 0.80, "pension": 0.55, "cash": 0.60}
DEPOSIT = {"transfer": (0.95, 1.0), "pension": (0.95, 1.0), "cash": (0.40, 0.90)}
LENDER_TYPE = {"Consumer credit": "NBFC", "Credit card": "BANK", "Car loan": "NBFC", "Mortgage": "BANK",
               "Microloan": "MFI", "Loan for business development": "BANK"}
BUREAU_STATUS = {"Active": "ACTIVE", "Closed": "CLOSED", "Sold": "WRITTEN_OFF", "Bad debt": "WRITTEN_OFF"}
GRID = {"0": "000", "1": "030", "2": "060", "3": "090", "4": "120", "5": "150", "X": P.GRID_NOT_REPORTED}
INTERNAL_LENDER = "SAMRUDDHI FINANCE"     # fictional stand-in for the originating lender
APP_COLUMNS = ["SK_ID_CURR", "TARGET", "NAME_CONTRACT_TYPE", "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY",
               "NAME_INCOME_TYPE", "OCCUPATION_TYPE", "DAYS_BIRTH", "DAYS_EMPLOYED", "CNT_CHILDREN",
               "REGION_RATING_CLIENT", "FLAG_OWN_REALTY", "FLAG_OWN_CAR", "AMT_REQ_CREDIT_BUREAU_YEAR"]


def paise(value) -> int | None:
    """A Home Credit amount (float in the source file) to rescaled integer paise."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return int((Decimal(repr(float(value))) * SCALE * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def months_ago(days: float) -> int:
    """Days relative to the application (negative = before) to a relative month (-1 = last month)."""
    return int((Decimal(repr(float(days))) / DAYS_PER_MONTH).to_integral_value(rounding="ROUND_FLOOR"))


def quantile_draw(rng: random.Random, levels: list[float], values: list[float]) -> float:
    """Inverse-CDF draw from a quantile table, interpolating between levels."""
    u = min(max(rng.random(), levels[0]), levels[-1])
    i = max(1, bisect_left(levels, u))
    lo, hi = levels[i - 1], levels[i]
    w = (u - lo) / (hi - lo) if hi > lo else 0.0
    return values[i - 1] + w * (values[i] - values[i - 1])


def _read(raw: Path, table: str, columns: list[str], ids: set | None = None, key: str = "SK_ID_CURR") -> pd.DataFrame:
    files = sorted((raw / "home_credit" / table).glob("*.parquet"))
    frames = []
    for f in files:
        frame = pd.read_parquet(f, columns=columns)
        if ids is not None:
            frame = frame[frame[key].isin(ids)]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def load(raw: Path, n: int) -> dict:
    app = _read(raw, "application_train_dated", APP_COLUMNS)
    app = app.sort_values("SK_ID_CURR")
    app = app.sample(n=min(n, len(app)), random_state=SEED).sort_values("SK_ID_CURR")
    ids = set(app["SK_ID_CURR"])
    bureau = _read(raw, "bureau", ["SK_ID_CURR", "SK_ID_BUREAU", "CREDIT_ACTIVE", "CREDIT_TYPE", "DAYS_CREDIT",
                                   "DAYS_CREDIT_ENDDATE", "CREDIT_DAY_OVERDUE", "AMT_CREDIT_MAX_OVERDUE",
                                   "AMT_CREDIT_SUM", "AMT_CREDIT_SUM_DEBT", "AMT_ANNUITY"], ids)
    balance = _read(raw, "bureau_balance", ["SK_ID_BUREAU", "MONTHS_BALANCE", "STATUS"],
                    set(bureau["SK_ID_BUREAU"]), key="SK_ID_BUREAU")
    balance = balance[balance["MONTHS_BALANCE"] >= -P.HISTORY_MONTHS]
    inst = _read(raw, "installments_payments", ["SK_ID_CURR", "SK_ID_PREV", "DAYS_INSTALMENT",
                                                "DAYS_ENTRY_PAYMENT", "AMT_INSTALMENT", "AMT_PAYMENT"], ids)
    prev = _read(raw, "previous_application", ["SK_ID_CURR", "SK_ID_PREV", "NAME_CONTRACT_STATUS"], ids)
    return {"app": app, "bureau": bureau, "balance": balance, "inst": inst, "prev": prev}


def _group(frame: pd.DataFrame, key: str) -> dict:
    return {k: g for k, g in frame.groupby(key, sort=True)}


def _tradelines(person_id: str, bureau: pd.DataFrame | None, grids: dict,
                app_month: int) -> tuple[list[dict], dict, list[tuple]]:
    """Real bureau rows in the shared tradeline format, per-month delinquency events, and
    (id, lender type, EMI, first relative month, last relative month, active) for each loan that
    had a payment in the statement window."""
    rows, events, specs = [], defaultdict(list), []
    if bureau is None:
        return rows, events, specs
    for b in bureau.sort_values("SK_ID_BUREAU").itertuples():
        tid = f"{person_id}-K{b.SK_ID_BUREAU}"
        opened = months_ago(b.DAYS_CREDIT)
        end = months_ago(b.DAYS_CREDIT_ENDDATE) if not pd.isna(b.DAYS_CREDIT_ENDDATE) else None
        status = BUREAU_STATUS.get(b.CREDIT_ACTIVE, "CLOSED")
        debt = paise(b.AMT_CREDIT_SUM_DEBT) or 0
        annuity = paise(b.AMT_ANNUITY)
        if annuity and annuity > 0:
            emi_minor, basis = annuity, "REPORTED"
        elif status == "ACTIVE" and debt > 0:
            if b.CREDIT_TYPE == "Credit card":
                emi_minor = scale(debt, 0.05)
            else:
                emi_minor = debt // max(1, end if end and end > 0 else 12)
            basis = "ESTIMATED"
        else:
            emi_minor, basis = 0, "NONE"
        grid = grids.get(b.SK_ID_BUREAU, {})
        cells = []
        for rel in range(-P.HISTORY_MONTHS, 0):
            if rel in grid:
                code = grid[rel]
                cells.append(P.GRID_NOT_OPEN if code == "C" else GRID.get(code, P.GRID_NOT_REPORTED))
                if code in "12345":
                    events[rel].append(tid)
            elif rel < opened or (status != "ACTIVE" and end is not None and rel > end):
                cells.append(P.GRID_NOT_OPEN)
            else:
                cells.append(P.GRID_NOT_REPORTED)
        payment = emi_minor
        if not payment and end is not None and end > opened and b.CREDIT_TYPE != "Credit card":
            payment = (paise(b.AMT_CREDIT_SUM) or 0) // (end - opened)
        last = -1 if status == "ACTIVE" else (end if end is not None else opened)
        if payment > 0 and last >= -P.STATEMENT_MONTHS:
            specs.append((tid, LENDER_TYPE.get(b.CREDIT_TYPE, "NBFC"), payment, opened + 1, min(last, -1),
                          status == "ACTIVE"))
        rows.append({
            "tradeline_id": tid, "lender_type": LENDER_TYPE.get(b.CREDIT_TYPE, "NBFC"),
            "loan_kind": str(b.CREDIT_TYPE).lower().replace(" ", "_"), "opened_month": month_label(app_month + opened),
            "sanctioned_minor": paise(b.AMT_CREDIT_SUM) or 0, "emi_minor": emi_minor if status == "ACTIVE" else 0,
            "tenure_months": max(0, end - opened) if end is not None else 0, "status": status,
            "outstanding_minor": debt if status == "ACTIVE" else 0, "dpd_grid": "|".join(cells),
            "emi_basis": basis,
            "current_overdue_days": int(b.CREDIT_DAY_OVERDUE) if not pd.isna(b.CREDIT_DAY_OVERDUE) else "",
        })
    return rows, events, specs


def _internal(inst: pd.DataFrame | None, prev: pd.DataFrame | None) -> tuple[dict, dict, list]:
    """Real repayment history with the lender: features, per-month late events, active instalments."""
    feats = {"hc_prev_applications": 0, "hc_prev_refused": 0, "hc_instalments_12m": 0,
             "hc_late_share_12m": "", "hc_short_share_12m": "", "hc_max_days_late_12m": "",
             "hc_late_share_all": "", "hc_history_status": P.NO_RECORD}
    events: dict = defaultdict(list)
    active: list = []
    if prev is not None:
        feats["hc_prev_applications"] = len(prev)
        feats["hc_prev_refused"] = int((prev["NAME_CONTRACT_STATUS"] == "Refused").sum())
    if inst is None or inst.empty:
        return feats, events, active
    inst = inst.dropna(subset=["DAYS_INSTALMENT"])
    late = inst["DAYS_ENTRY_PAYMENT"] > inst["DAYS_INSTALMENT"]
    short = inst["AMT_PAYMENT"] < inst["AMT_INSTALMENT"] - 1
    recent = inst["DAYS_INSTALMENT"] >= -365
    feats["hc_history_status"] = P.OBSERVED
    feats["hc_late_share_all"] = ratio(int(late.sum()), len(inst))
    if recent.any():
        r = inst[recent]
        feats["hc_instalments_12m"] = int(len(r))
        feats["hc_late_share_12m"] = ratio(int(late[recent].sum()), len(r))
        feats["hc_short_share_12m"] = ratio(int(short[recent].sum()), len(r))
        days_late = (r["DAYS_ENTRY_PAYMENT"] - r["DAYS_INSTALMENT"]).clip(lower=0).fillna(0)
        feats["hc_max_days_late_12m"] = int(days_late.max())
    for row in inst[recent & (late | short)].itertuples():
        events[months_ago(row.DAYS_INSTALMENT)].append(f"HC{row.SK_ID_PREV}")
    window = inst[recent].copy()
    window["rel"] = window["DAYS_INSTALMENT"].map(months_ago)
    for prev_id, g in window.groupby("SK_ID_PREV", sort=True):
        amount = paise(float(g["AMT_INSTALMENT"].median()))
        if amount:
            last = int(g["rel"].max())
            active.append((f"HC{prev_id}", "NBFC", amount, int(g["rel"].min()), min(last, -1), last >= -2))
    return feats, events, active


def _statement(person, rng: random.Random, months: int, loans: list[Loan], events: dict,
               cal: dict, inject: dict) -> list[BankMonth]:
    """Synthetic statement months -months..-1, reconciled to the paisa."""
    style = cal["styles"][person.style]
    levels = cal["quantile_levels"]
    cv = quantile_draw(rng, levels, style["income_cv_quantiles"])
    cv = min(cv, 1.5)
    buffer_months = min(quantile_draw(rng, levels, style["buffer_months_quantiles"]), 12.0)
    share = rng.uniform(*DEPOSIT[person.style])
    inject["income_cv"], inject["deposit_share"] = round(cv, 4), round(share, 4)
    level = scale(person.base_income, share)
    balance = scale(level, buffer_months * rng.uniform(0.8, 1.2))
    out = []
    duplicate_at = rng.randrange(months) if inject["duplicate_import"] else -1
    for i, rel in enumerate(range(-months, 0)):
        bm = BankMonth(month=person.app_month + rel, opening=balance)
        if rng.random() < style["zero_income_month_share"]:
            income = 0
        else:
            income = scale(level, max(0.0, 1.0 + rng.gauss(0.0, cv)))
        bm.income_lines = split_income(person, income, rng)
        bounced = set(events.get(rel, []))
        for loan in loans:
            if not loan.start < person.app_month + rel <= loan.start + loan.tenure:
                continue
            if loan.loan_id in bounced:
                bm.returns.append((loan.loan_id, loan.emi))
                bm.charges += P.BOUNCE_CHARGE
            else:
                bm.loan_debits.append((loan.loan_id, loan.emi, False))
        if bm.returns:
            target = scale(level, rng.uniform(0.0, 0.02))        # the money was not there
        else:
            target = scale(level, buffer_months * max(0.2, 1.0 + rng.gauss(0.0, 0.15)))
        residual = balance + bm.credits() - bm.debits() - target
        if residual >= 0:
            bm.spend = scale(residual, rng.uniform(0.55, 0.85))
            bm.atm = residual - bm.spend
        else:
            bm.cash_deposit = -residual
        if inject["round_trip"] and rng.random() < 0.5:
            bm.round_trip = round_to(scale(max(income, level), rng.uniform(0.5, 1.5)), rupees(1000))
        if inject["window_dressing"] and i == months - 1:
            bm.window_dressing = round_to(scale(person.base_income, rng.uniform(1.5, 3.0)), rupees(1000))
        bm.closing = balance + bm.credits() - bm.debits()
        if i == duplicate_at and bm.income_lines:
            bm.duplicate_credit = rng.choice(bm.income_lines)
        balance = target
        out.append(bm)
    return out


def build(raw: Path, out: Path, n: int, transaction_sample: int) -> dict:
    cal = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    data = load(raw, n)
    bureau_by = _group(data["bureau"], "SK_ID_CURR")
    grids: dict = defaultdict(dict)
    for row in data["balance"].itertuples():
        grids[row.SK_ID_BUREAU][int(row.MONTHS_BALANCE)] = str(row.STATUS)
    inst_by = _group(data["inst"], "SK_ID_CURR")
    prev_by = _group(data["prev"], "SK_ID_CURR")

    tables = {name: [] for name in ("applications", "monthly_cashflow", "bureau_tradelines", "gst_filings",
                                    "vouches", "outcomes", "injections", "features", "transactions")}
    with_statement = 0
    for a in data["app"].itertuples():
        sk = int(a.SK_ID_CURR)
        rng = random.Random(f"{SEED}:H{sk}")
        person_id = f"H{sk:06d}"
        cohort = P.COHORTS[rng.randrange(len(P.COHORTS))]
        app_month = cohort[0] * 12 + cohort[1] - 1
        style = INCOME_STYLE.get(a.NAME_INCOME_TYPE, "cash")
        income = paise(a.AMT_INCOME_TOTAL)
        person = SimpleNamespace(borrower_id=person_id, segment=NARRATION_SEGMENT[style], style=style,
                                 base_income=income, urban=int(a.REGION_RATING_CLIENT) == 1, app_month=app_month)

        tradelines, bureau_events, specs = _tradelines(person_id, bureau_by.get(sk), grids, app_month)
        hc, hc_events, hc_active = _internal(inst_by.get(sk), prev_by.get(sk))
        events = defaultdict(list)
        for source in (bureau_events, hc_events):
            for rel, ids in source.items():
                events[rel].extend(ids)

        loans = []
        for loan_id, lender_type, amount, first, last, active in specs + hc_active:
            names = P.LENDER_NAMES[lender_type]
            lender = INTERNAL_LENDER if loan_id.startswith("HC") else names[sk % len(names)]
            loan = Loan(loan_id, "internal_previous" if loan_id.startswith("HC") else "bureau_tradeline",
                        lender_type, lender, 0, Decimal(0), last - first + 1, amount, app_month + first - 1,
                        2 + sk % 9, True, active)
            loans.append(loan)

        inject = {"borrower_id": person_id, "style": style, "statement_months": 0, "income_cv": "",
                  "deposit_share": "", "hidden_loan_emi_minor": 0, "forgot_loan_emi_minor": 0,
                  "window_dressing": int(rng.random() < 0.03), "round_trip": int(style == "cash" and rng.random() < 0.05),
                  "duplicate_import": int(rng.random() < 0.03)}
        if rng.random() < 0.05:   # undisclosed digital loan: in the statement, not in the bureau
            hidden = scale(income, rng.uniform(0.04, 0.12))
            loans.append(Loan(f"{person_id}-X1", "fintech_app", "FINTECH", rng.choice(P.LENDER_NAMES["FINTECH"]),
                              0, Decimal(0), 12, hidden, app_month - 8, 7, False, False))
            inject["hidden_loan_emi_minor"] = hidden

        running = [loan for loan in loans if loan.declared or loan.loan_id.endswith("-X1")]
        true_existing = sum(loan.emi for loan in running)
        visible = sorted((loan for loan in running if loan.declared), key=lambda x: x.emi)
        declared_emi = sum(loan.emi for loan in visible)
        if visible and rng.random() < P.P_UNDISCLOSED_LOAN:
            declared_emi -= visible[0].emi
            inject["forgot_loan_emi_minor"] = visible[0].emi

        p_link = P_LINK[style] * (1.1 if a.DAYS_BIRTH > -35 * 365 else 0.9)
        if rng.random() < min(0.95, p_link):
            months = P.STATEMENT_MONTHS if rng.random() < P.P_FULL_STATEMENT else rng.choice(P.PARTIAL_STATEMENT_MONTHS)
            status = P.OBSERVED if months == P.STATEMENT_MONTHS else P.PARTIAL
        else:
            months, status = 0, P.NOT_PROVIDED
        inject["statement_months"] = months
        bank = _statement(person, rng, months, loans, events, cal, inject) if months else []

        gst = []
        if a.NAME_INCOME_TYPE in ("Commercial associate", "Businessman") and rng.random() < 0.45:
            under = rng.uniform(0.75, 1.0)
            for rel in range(-P.STATEMENT_MONTHS, 0):
                if rng.random() < P.P_GST_MISSED:
                    gst.append({"month": month_label(app_month + rel), "status": "MISSED", "turnover_minor": None})
                else:
                    turnover = scale(income, under / 0.15 * max(0.3, 1.0 + rng.gauss(0.0, 0.12)))
                    gst.append({"month": month_label(app_month + rel), "status": "FILED",
                                "turnover_minor": round_to(turnover, rupees(100))})

        employed = int(a.DAYS_EMPLOYED)
        tenure_months = None if employed == 365243 else max(0, -employed) * 12 // 365
        age = -int(a.DAYS_BIRTH) // 365
        age_band = "21-25" if age <= 25 else "26-35" if age <= 35 else "36-45" if age <= 45 else "46-60" if age <= 60 else "60+"
        new_emi = paise(a.AMT_ANNUITY)
        credit = paise(a.AMT_CREDIT)
        app = {
            "borrower_id": person_id, "application_month": month_label(app_month),
            "occupation": str(a.NAME_INCOME_TYPE).lower().replace(" ", "_"),
            "occupation_type": "" if pd.isna(a.OCCUPATION_TYPE) else str(a.OCCUPATION_TYPE),
            "state": "", "urban": int(person.urban), "age_band": age_band, "dependents": int(a.CNT_CHILDREN),
            "product": str(a.NAME_CONTRACT_TYPE).lower().replace(" ", "_"), "requested_amount_minor": credit,
            "tenure_months": int((Decimal(credit) / Decimal(new_emi)).to_integral_value()) if new_emi else "",
            "rate_annual": "", "new_emi_minor": new_emi or 0, "currency": P.CURRENCY,
            "declared_income_minor": income, "declared_income_status": P.OBSERVED,
            "declared_emi_minor": max(0, declared_emi), "declared_emi_status": P.OBSERVED,
            "occupation_tenure_months": tenure_months,
            "occupation_tenure_status": P.NOT_APPLICABLE if tenure_months is None else P.OBSERVED,
            "bank_statement_status": status,
        }
        monthly = [{
            "borrower_id": person_id, "month": month_label(bm.month), "credits_minor": bm.credits(),
            "debits_minor": bm.debits(), "emi_debits_minor": sum(x for _, x, _ in bm.loan_debits),
            "emi_bounces": len(bm.returns), "bounce_charges_minor": bm.charges,
            "disbursal_credits_minor": 0, "disbursal_count": 0,
            "opening_balance_minor": bm.opening, "closing_balance_minor": bm.closing,
        } for bm in bank]
        features = build_features(app, monthly, tradelines, gst, [])
        features.update(hc)
        features["occupation_type"] = app["occupation_type"]
        features["owns_realty"] = int(a.FLAG_OWN_REALTY == "Y")
        features["region_rating"] = int(a.REGION_RATING_CLIENT)
        features["bureau_enquiries_12m"] = "" if pd.isna(a.AMT_REQ_CREDIT_BUREAU_YEAR) else int(a.AMT_REQ_CREDIT_BUREAU_YEAR)
        features["bureau_current_overdue_max"] = max((t["current_overdue_days"] for t in tradelines
                                                      if t["current_overdue_days"] != ""), default="")
        app["legacy_decision"], app["legacy_reason"] = features["legacy_decision"], features["legacy_reason"]
        inject["true_existing_emi_minor"] = true_existing

        tables["applications"].append(app)
        tables["monthly_cashflow"].extend(monthly)
        tables["bureau_tradelines"].extend({"borrower_id": person_id, **t} for t in tradelines)
        tables["gst_filings"].extend({"borrower_id": person_id, **g} for g in gst)
        tables["outcomes"].append({"borrower_id": person_id, "default_12m": int(a.TARGET), "default_month": "",
                                   "max_dpd_12m": ""})
        tables["injections"].append(inject)
        tables["features"].append(features)
        if bank and with_statement < transaction_sample:
            with_statement += 1
            loan_map = {loan.loan_id: loan for loan in loans}
            counter = [0]
            tx_rng = random.Random(f"{SEED}:H{sk}:txn")
            for bm in bank:
                tables["transactions"].extend(to_transactions(person, bm, loan_map, tx_rng, counter))

    by_borrower: dict[str, list[dict]] = defaultdict(list)
    for t in tables["bureau_tradelines"]:
        by_borrower[t["borrower_id"]].append(t)
    tables["bureau_trajectory"] = [row for app in tables["applications"] if by_borrower[app["borrower_id"]]
                                   for row in trajectory_rows(app["borrower_id"], app["application_month"],
                                                              by_borrower[app["borrower_id"]])]
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, rows in tables.items():
        path = out / f"{name}.csv"
        write_csv(path, rows)
        files[f"{name}.csv"] = {"rows": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {
        "dataset": "anchored", "builder_version": VERSION, "seed": SEED, "borrowers": len(tables["applications"]),
        "base": "Home Credit Default Risk (application_train), HF mirror revision pinned in download.py",
        "label": "default_12m = Home Credit TARGET: payment difficulties on the loan (late beyond the lender's threshold on early instalments)",
        "money_unit": f"integer paise; Home Credit amounts x {SCALE}", "currency": P.CURRENCY,
        "real_tables": ["applications (except bank_statement_status, declared_emi_*)", "bureau_tradelines", "outcomes",
                        "bureau_trajectory (derived month by month from the real grids; no score)",
                        "features: bureau_*, hc_*, application fields"],
        "synthetic_tables": ["monthly_cashflow", "transactions", "gst_filings", "injections",
                             "features: bank_*, gst_*, declared_to_bank_income, undeclared_emi_to_income"],
        "notice": "Real anonymised applicants with synthetic statements. Illustrative only, not financial advice. Do not commit.",
        "files": files,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the anchored (real + synthetic) dataset.")
    parser.add_argument("--n", type=int, default=30_000)
    parser.add_argument("--raw", type=Path, default=Path("../data/external"))
    parser.add_argument("--out", type=Path, default=Path("../data/anchored"))
    parser.add_argument("--transactions", type=int, default=300)
    args = parser.parse_args()
    manifest = build(args.raw, args.out, args.n, args.transactions)
    for name, meta in manifest["files"].items():
        print(f"{name:24} {meta['rows']:>9} rows")


if __name__ == "__main__":
    main()
