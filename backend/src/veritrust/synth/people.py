"""Stage 1: sample each borrower's hidden traits and the loans they already carry."""

import math
import random

from . import params as P
from .model import Borrower, Loan, month_index
from .money import emi, round_to, rupees, scale

AGE_WEIGHTS = {
    "salaried_formal": (0.15, 0.45, 0.28, 0.12),
    "gig_platform": (0.35, 0.45, 0.15, 0.05),
    "kirana_msme": (0.05, 0.35, 0.35, 0.25),
    "smallholder_farmer": (0.05, 0.25, 0.35, 0.35),
    "informal_daily_wage": (0.15, 0.40, 0.30, 0.15),
}
AGE_INCOME = {"21-25": 0.80, "26-35": 1.0, "36-45": 1.10, "46-60": 1.05}
AGE_TENURE = {"21-25": 18, "26-35": 48, "36-45": 96, "46-60": 150}
EMI_DAYS = (2, 5, 7, 10)


def pick(rng: random.Random, weights: dict) -> str:
    """Weighted choice over a dict of key -> weight, in insertion order (deterministic)."""
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def poisson(rng: random.Random, lam: float) -> int:
    """Knuth's Poisson sampler; fine for the small rates used here."""
    limit, k, product = math.exp(-lam), 0, rng.random()
    while product > limit:
        k += 1
        product *= rng.random()
    return k


def lognormal(rng: random.Random, median: float, sd: float) -> float:
    return median * math.exp(rng.gauss(0.0, sd))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def new_loan(rng: random.Random, borrower_id: str, n: int, kind: str, base_income: int,
             start: int, declared: bool = True) -> Loan:
    """A loan of `kind` sized off monthly income, disbursed in month `start`."""
    lender_type, rate, tenures, (mult, sd), p_report = P.LOAN_KINDS[kind]
    principal = round_to(scale(base_income, lognormal(rng, mult, sd)), rupees(500))
    tenure = rng.choice(tenures)
    return Loan(
        loan_id=f"{borrower_id}-L{n:02d}", kind=kind, lender_type=lender_type,
        lender=rng.choice(P.LENDER_NAMES[lender_type]), principal=principal, rate=rate,
        tenure=tenure, emi=emi(principal, rate, tenure), start=start,
        emi_day=rng.choice(EMI_DAYS), reported=rng.random() < p_report, declared=declared,
    )


def sample_borrower(index: int, rng: random.Random) -> Borrower:
    """Draw one borrower. `rng` must be seeded per borrower so ids stay stable across sizes."""
    borrower_id = f"B{index:06d}"
    segment = pick(rng, {k: v["weight"] for k, v in P.SEGMENTS.items()})
    seg = P.SEGMENTS[segment]
    state = pick(rng, {k: v[0] for k, v in P.STATES.items()})
    _, state_income, urban_mult = P.STATES[state]
    urban = rng.random() < min(0.98, seg["urban"] * urban_mult)
    age_band = rng.choices(P.AGE_BANDS, weights=AGE_WEIGHTS[segment])[0]
    dependents = rng.choices((0, 1, 2, 3, 4), weights=(0.2, 0.25, 0.3, 0.17, 0.08))[0]
    cohort = P.COHORTS[rng.randrange(len(P.COHORTS))]
    app_month = month_index(*cohort)

    median, sd = seg["income"]
    urban_factor = 1.15 if urban else 0.90
    if segment == "smallholder_farmer":
        urban_factor = 1.0
    monthly = lognormal(rng, median * state_income * urban_factor * AGE_INCOME[age_band], sd)
    base_income = round_to(rupees(int(monthly)), rupees(100))

    discipline = rng.betavariate(4.0, 1.8)
    expense_mean, expense_sd = seg["expense"]
    expense_ratio = clamp(rng.gauss(expense_mean + 0.02 * (dependents - 2), expense_sd), 0.35, 0.92)
    lo, hi = seg["deposit"]
    inflator = rng.random() < seg["inflator"] * (1.5 if discipline < 0.55 else 0.8)

    sim_start = app_month - P.HISTORY_MONTHS
    savings = scale(base_income, P.BUFFER_SCALE * seg["buffer_months"] * lognormal(rng, 1.0, 0.6) * (0.5 + discipline))

    borrower = Borrower(
        borrower_id=borrower_id, segment=segment, state=state, urban=urban, age_band=age_band,
        dependents=dependents, app_month=app_month, base_income=base_income,
        cv=seg["cv"] * lognormal(rng, 1.0, 0.3), expense_ratio=expense_ratio,
        discipline=discipline, save_rate=clamp(rng.gauss(0.15 + 0.35 * discipline, 0.05), 0.02, 0.6),
        deposit_share=rng.uniform(lo, hi),
        margin=rng.uniform(*seg["margin"]) if "margin" in seg else 1.0,
        stacker=rng.random() < seg["stacker"] * (1.5 if discipline < 0.6 else 0.7),
        inflator=inflator,
        window_dresser=rng.random() < P.P_WINDOW_DRESSING + (0.25 if inflator else 0.0),
        round_tripper=segment == "kirana_msme" and rng.random() < P.P_ROUND_TRIP + (0.2 if inflator else 0.0),
        duplicate_import=rng.random() < P.P_DUPLICATE_IMPORT,
        gst_registered=segment == "kirana_msme" and rng.random() < seg["p_gst"] * (1.2 if urban else 0.7),
        gst_underreport=rng.uniform(0.75, 1.0),
        community=rng.random() < seg["community"], macro_exposed=False,
        tenure_months=max(1, int(lognormal(rng, AGE_TENURE[age_band] * (1.3 if segment == "smallholder_farmer" else 1.0), 0.5))),
        savings=savings, credit_history_start=None, prior_closed_loans=0,
        bonus=segment == "salaried_formal" and rng.random() < 0.4,
    )

    if rng.random() < seg["p_prior"]:
        borrower.prior_closed_loans = 1 + poisson(rng, 1.0)
        borrower.credit_history_start = sim_start - rng.randint(6, 120)

    for _ in range(poisson(rng, seg["access"])):
        kind = pick(rng, seg["kinds"])
        loan = new_loan(rng, borrower_id, len(borrower.loans) + 1, kind, base_income, sim_start)
        elapsed = rng.randint(0, loan.tenure - 1)
        loan.start = sim_start - elapsed
        loan.paid = loan.dues_by(sim_start)
        borrower.loans.append(loan)

    # Lenders sized past loans to a debt cap; stackers are the ones who slipped past it.
    if not borrower.stacker:
        cap = scale(base_income, 0.45)
        borrower.loans.sort(key=lambda loan: loan.emi)
        while borrower.loans and sum(loan.emi for loan in borrower.loans) > cap:
            borrower.loans.pop()

    reported_starts = [loan.start for loan in borrower.loans if loan.reported]
    if reported_starts:
        earliest = min(reported_starts)
        if borrower.credit_history_start is None or earliest < borrower.credit_history_start:
            borrower.credit_history_start = earliest
    return borrower
