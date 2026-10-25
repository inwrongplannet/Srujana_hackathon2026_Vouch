"""Stage 1b: plan one shock, shortly before the application, for a share of borrowers.

Why a plan rather than a monthly coin flip: the question this data answers is "the bureau score
fell after a shock; does the vouch still carry information?", which needs enough shocked
applicants whose score drop lands before they apply. The plan is hidden truth; lenders only see
its traces (missed EMIs, new enquiries, a lower score, endorsers who stay or leave).
"""

import random

from . import params as P
from .model import Borrower, ShockPlan
from .money import scale
from .people import lognormal, pick


def stratum(b: Borrower) -> str:
    """'active_credit' when a reported loan is still running six months before the application."""
    live = any(loan.reported and loan.start + loan.tenure >= b.app_month - 6 for loan in b.loans)
    return "active_credit" if live else "other"


def plan_shock(b: Borrower, rng: random.Random, force: bool = False) -> ShockPlan | None:
    """A shock for SHOCK_SHARE of each stratum, starting SHOCK_LEAD months before they apply.

    Borrowers with live credit are oversampled because only they can show a bureau-score drop;
    `sample_weight` undoes the oversampling.
    """
    if rng.random() >= P.SHOCK_SHARE[stratum(b)] and not force:
        return None
    kind = pick(rng, P.SHOCK_TYPES[b.segment])
    severity = rng.choices((1, 2, 3), weights=P.SHOCK_SEVERITY)[0]
    longest, shortest = P.SHOCK_LEAD
    start = b.app_month - rng.randint(shortest, longest)
    if kind in P.EXPENSE_SHOCKS:
        insured = kind == "MEDICAL" and rng.random() < P.P_INSURED[b.segment]
        cost = scale(b.base_income, P.SHOCK_EXPENSE[severity] * lognormal(rng, 1.0, 0.25))
        if insured:
            cost = scale(cost, 1.0 - P.INSURED_COVER)
        return ShockPlan(kind=kind, severity=severity, insured=insured, start=start, months=1,
                         expense=cost, income_factor=1.0)
    factor, months = P.SHOCK_INCOME[severity]
    cost = scale(b.base_income, P.SHOCK_EXPENSE[severity] * P.SHOCK_INCOME_COST * lognormal(rng, 1.0, 0.25))
    return ShockPlan(kind=kind, severity=severity, insured=False, start=start, months=months,
                     expense=cost, income_factor=factor)
