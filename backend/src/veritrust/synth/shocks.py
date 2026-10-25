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
    insured = rng.random() < P.P_INSURED[b.urban]
    if kind == "MEDICAL":
        # NSS out-of-pocket cost for public, average or private care; already net of insurance.
        cost = int(P.SHOCK_MEDICAL_MINOR[severity][b.urban] * lognormal(rng, 1.0, 0.25))
        return ShockPlan(kind=kind, severity=severity, insured=insured, start=start, months=1,
                         expense=cost, income_factor=1.0)
    if kind == "FAMILY":
        months_of_income = P.SHOCK_FAMILY_MONTHS * lognormal(rng, 1.0, P.SHOCK_FAMILY_SD)
        severity = 1 if months_of_income < 3 else 2 if months_of_income < 5 else 3
        return ShockPlan(kind=kind, severity=severity, insured=False, start=start, months=1,
                         expense=scale(b.base_income, months_of_income), income_factor=1.0)
    if kind == "JOB_LOSS":
        # No pay until back in work: geometric spell at the PLFS re-employment rate.
        months = 1
        while rng.random() >= P.REEMPLOY_MONTHLY and months < 4 * P.PERFORMANCE_MONTHS:
            months += 1
        severity = 1 if months <= 3 else 2 if months <= 9 else 3
        return ShockPlan(kind=kind, severity=severity, insured=False, start=start, months=months,
                         expense=0, income_factor=0.0)
    if kind == "CROP":
        # One season at the unirrigated drought factor (Economic Survey 2017-18).
        return ShockPlan(kind=kind, severity=severity, insured=False, start=start, months=6,
                         expense=0, income_factor=P.DROUGHT_CROP_FACTOR[False])
    factor, months = P.SHOCK_BUSINESS[severity]   # ASSUMPTION: no source for business disruption
    return ShockPlan(kind=kind, severity=severity, insured=False, start=start, months=months,
                     expense=0, income_factor=factor)
