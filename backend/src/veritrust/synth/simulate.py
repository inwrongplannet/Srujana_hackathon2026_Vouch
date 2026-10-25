"""Stage 2: live each borrower's months. Default is never a rule; it emerges when cash runs out.

Each month: income arrives (season, noise, personal shocks, macro events), essentials are paid
(sticky, they do not fall with income), EMIs are attempted (bounce if cash is short), arrears are
caught up when there is room, and part of any surplus is spent. All money is integer paise.
"""

import math
import random
from dataclasses import dataclass, field

from . import params as P
from .behaviour import MonthEffects, step
from .model import Borrower, Loan, year_month
from .money import emi, round_to, rupees, scale
from .people import clamp, lognormal, new_loan, pick

SHOCK_NAMES = {
    "salaried_formal": "job_loss",
    "gig_platform": "platform_deactivation",
    "kirana_msme": "illness_shop_closed",
    "smallholder_farmer": "illness",
    "informal_daily_wage": "illness",
}
# Who gets paid first when cash is short: group pressure and repossession risk come first.
PRIORITY = {"mfi_jlg": 3.0, "two_wheeler": 2.5, "bank_personal": 2.0, "nbfc_consumer": 2.0,
            "fintech_app": 1.5, "kcc_crop": 1.0, "bnpl": 1.0, "gold_loan": 0.5}
NEW_LOAN_PRIORITY = 2.2


@dataclass
class Payment:
    loan_id: str
    amount: int
    manual: bool          # True for a caught-up overdue paid by UPI, False for an EMI auto-debit


@dataclass
class MonthTrue:
    """What really happened in one month (hidden; the observation layer derives the views)."""

    month: int
    income: int
    essentials: int
    essentials_shortfall: int
    discretionary: int
    payments: list[Payment] = field(default_factory=list)
    bounces: list[tuple[str, int]] = field(default_factory=list)   # (loan_id, attempted amount)
    charges: int = 0
    disbursals: list[tuple[str, int]] = field(default_factory=list)  # (loan_id, net credited)
    informal_support: int = 0
    vouch_support: int = 0        # help mobilised by the borrower's endorsers
    windfall: int = 0
    events: list[tuple[str, str]] = field(default_factory=list)   # (category, name) from behaviour.py
    shock: str = ""
    lumpy: str = ""
    savings_end: int = 0


@dataclass
class SimState:
    savings: int
    shock_left: int = 0
    harvest: dict = field(default_factory=dict)
    loan_counter: int = 0
    # Separate stream for the shock and vouch mechanics, so the original draws stay reproducible.
    aux: random.Random = field(default_factory=random.Random)
    behind: int = 0               # consecutive months with a bounced EMI


def _harvest_factor(b: Borrower, year: int, cal: int, rng: random.Random, st: SimState) -> float:
    season = ("kharif", year) if cal in (10, 11) else ("rabi", year)
    if season not in st.harvest:
        factor = lognormal(rng, 1.0, 0.18)
        if rng.random() < 0.06:
            factor *= 0.5                      # idiosyncratic crop failure
        st.harvest[season] = factor
    factor = st.harvest[season]
    rain = P.RAINFALL_DEFICIT
    if b.macro_exposed and (year, cal) in rain["crop_months"]:
        factor *= rain["crop_factor"]
    return factor


def income_for(b: Borrower, month: int, rng: random.Random, st: SimState) -> tuple[int, str]:
    """Income in paise for `month`, and the shock name if a personal shock is active."""
    year, cal = year_month(month)
    base = b.base_income
    noise = 1.0 + rng.gauss(0.0, b.cv)
    if b.segment == "salaried_formal":
        amount = scale(base, noise)
        if b.bonus and cal == 3:
            amount += scale(base, rng.uniform(0.3, 1.0))
    elif b.segment == "gig_platform":
        factor = P.SEASON["gig_platform"].get(cal, 1.0) * noise
        if (year, cal) in P.GIG_INCENTIVE_CUT["months"]:
            factor *= P.GIG_INCENTIVE_CUT["factor"]
        amount = scale(base, factor)
    elif b.segment == "kirana_msme":
        amount = scale(base, P.SEASON["kirana_msme"].get(cal, 1.0) * noise)
    elif b.segment == "smallholder_farmer":
        amount = scale(base, float(P.FARM_NONCROP_SHARE) * noise)
        share = P.CROP_CALENDAR.get(cal)
        if share:
            amount += scale(base, 12 * share * _harvest_factor(b, year, cal, rng, st))
    else:
        days = clamp(rng.gauss(23 - (4 if cal in (7, 8) else 0), 2.5), 0, 28)
        factor = days / 23
        rain = P.RAINFALL_DEFICIT
        if b.macro_exposed and (year, cal) in rain["wage_months"]:
            factor *= rain["wage_factor"]
        amount = scale(base, factor * (1.0 + rng.gauss(0.0, b.cv / 2)))

    shock = ""
    if st.shock_left > 0:
        st.shock_left -= 1
        shock = SHOCK_NAMES[b.segment]
    elif rng.random() < b.shock_prob:
        st.shock_left = rng.randint(1, b.shock_max) - 1
        shock = SHOCK_NAMES[b.segment]
        if b.segment == "salaried_formal":
            b.base_income = scale(b.base_income, 0.95)   # re-employed a little lower
    if shock:
        amount = scale(amount, b.shock_factor)
    plan = b.shock
    if plan and plan.active(month) and plan.income_factor < 1.0:
        amount = scale(amount, plan.income_factor)
        shock = shock or plan.kind.lower()
    return amount, shock


def essentials_for(b: Borrower, month: int, rng: random.Random) -> tuple[int, str]:
    """Essential spending: sticky, sized off long-run income, with occasional lumpy costs."""
    _, cal = year_month(month)
    amount = scale(b.base_income, b.expense_ratio * (1.0 + rng.gauss(0.0, 0.04)))
    lumpy = ""
    if rng.random() < 0.04:
        amount += scale(b.base_income, rng.uniform(0.5, 2.0))
        lumpy = rng.choice(("medical", "wedding", "house_repair"))
    elif cal == 6 and b.dependents and rng.random() < 0.5:
        amount += scale(b.base_income, 0.15 * min(b.dependents, 3))
        lumpy = "school_fees"
    return amount, lumpy


def _open_new_digital_loan(b: Borrower, month: int, shortfall: int, rng: random.Random,
                           st: SimState) -> Loan:
    st.loan_counter += 1
    kind = "fintech_app" if rng.random() < 0.7 else "bnpl"
    loan = new_loan(rng, b.borrower_id, st.loan_counter, kind, b.base_income, month, declared=False)
    principal = min(round_to(max(scale(shortfall, rng.uniform(1.2, 2.5)), rupees(2000)), rupees(500)),
                    rupees(40_000))
    loan.principal = principal
    loan.emi = emi(principal, loan.rate, loan.tenure)
    b.loans.append(loan)
    if loan.reported:
        b.enquiries.append(month)
    return loan


def _shock_credit(b: Borrower, month: int, shortfall: int, st: SimState) -> Loan | None:
    """During or just after a shock, a borrower with a bureau file asks a lender for credit.

    Every request is a bureau enquiry; only some are approved. Returns the new loan, if any.
    """
    plan = b.shock
    if plan is None or not plan.start <= month < plan.start + plan.months + 2:
        return None
    if b.credit_history_start is None or b.credit_history_start > month:
        return None
    if st.aux.random() >= P.P_SHOCK_ENQUIRY:
        return None
    b.enquiries.append(month)
    if st.aux.random() >= P.P_ENQUIRY_APPROVED:
        return None
    st.loan_counter += 1
    kind = "nbfc_consumer" if st.aux.random() < 0.6 else "fintech_app"
    loan = new_loan(st.aux, b.borrower_id, st.loan_counter, kind, b.base_income, month, declared=False)
    principal = round_to(max(scale(shortfall, st.aux.uniform(1.0, 2.0)), rupees(3000)), rupees(500))
    loan.principal = principal
    loan.emi = emi(principal, loan.rate, loan.tenure)
    loan.reported = True
    b.loans.append(loan)
    return loan


def run_month(b: Borrower, month: int, rng: random.Random, st: SimState,
              organic_credit: bool) -> MonthTrue:
    """Simulate one month and update loans and savings in place."""
    plan = b.shock
    fx = step(b, b.traits, month, st.aux, plan is not None and month == plan.start) if b.traits else \
        MonthEffects(discipline=b.discipline)
    disc = fx.discipline
    income, shock = income_for(b, month, rng, st)
    income = scale(income, fx.income_factor)
    windfall = scale(b.base_income, fx.windfall)
    essentials, lumpy = essentials_for(b, month, rng)
    essentials += scale(b.base_income, fx.extra_cost)
    if fx.savings_lost:
        st.savings -= scale(st.savings, fx.savings_lost)
    savings = st.savings + income + windfall
    if plan and month == plan.start:
        drain = scale(st.savings, st.aux.uniform(*P.SHOCK_DRAIN_BY_SEVERITY[plan.severity]))
        essentials += plan.expense + drain
        lumpy = plan.kind.lower()

    due = [loan for loan in b.loans if not loan.written_off and loan.is_due(month)]
    due_total = sum(loan.emi for loan in due)

    # Disciplined borrowers trim essentials to protect their EMIs.
    if savings < essentials + due_total:
        trim = min(scale(essentials, 0.12 * disc), essentials + due_total - savings)
        essentials -= trim
    essentials_paid = min(essentials, savings)
    savings -= essentials_paid
    record = MonthTrue(month=month, income=income, essentials=essentials_paid,
                       essentials_shortfall=essentials - essentials_paid, discretionary=0,
                       shock=shock, lumpy=lumpy, windfall=windfall, events=fx.events)

    if savings < due_total:
        shock_loan = _shock_credit(b, month, due_total - savings, st)
        if shock_loan:
            net = shock_loan.principal - scale(shock_loan.principal, 0.02)
            savings += net
            record.disbursals.append((shock_loan.loan_id, net))
    if savings < due_total:
        shortfall = due_total - savings
        if b.stacker and rng.random() < 0.6 and \
                sum(1 for loan in b.loans if loan.lender_type == "FINTECH" and loan.is_open(month)) < 5:
            loan = _open_new_digital_loan(b, month, shortfall, rng, st)
            net = loan.principal - scale(loan.principal, 0.025)   # processing fee kept by lender
            savings += net
            record.disbursals.append((loan.loan_id, net))
        elif rng.random() < 0.15:
            record.informal_support = shortfall     # family or a moneylender; invisible to lenders
            savings += shortfall
    # Endorsers who stake their reputation also help, but only once trouble is visible: help
    # arrives the month after an EMI bounces, covering this month's dues and the arrears. So a
    # shock still reaches the bureau; the network decides how fast the borrower recovers. In a
    # regional disaster the endorsers are hit too, so help shrinks by the event's support factor.
    weight = b.vouch_weight.get(month, 0.0) * fx.support_factor
    overdue = sum(loan.emi * loan.arrears(month - 1) for loan in b.loans if not loan.written_off)
    if st.behind and weight > 0 and savings < due_total + overdue and st.aux.random() < 1.0 - math.exp(-weight):
        help_amount = min(due_total + overdue - savings, scale(b.base_income, P.VOUCH_SUPPORT_SHARE * weight))
        record.vouch_support = help_amount
        savings += help_amount

    if disc > 0.5:
        due.sort(key=lambda loan: (-(NEW_LOAN_PRIORITY if loan.is_new else PRIORITY[loan.kind]), loan.loan_id))
    else:
        rng.shuffle(due)
    paid_total = 0
    tech_bounce = fx.tech_bounce
    for loan in due:
        willful_skip = rng.random() < (1.0 - disc) * 0.05
        if loan.arrears(month - 1) >= 2 and disc < 0.5:
            willful_skip = willful_skip or rng.random() < 0.4   # disengages once behind
        glitch = tech_bounce and savings >= loan.emi   # the bank fails the debit; money was there
        tech_bounce = tech_bounce and not glitch
        if savings >= loan.emi and not willful_skip and not glitch:
            savings -= loan.emi
            loan.paid += 1
            paid_total += loan.emi
            record.payments.append(Payment(loan.loan_id, loan.emi, manual=False))
        else:
            record.bounces.append((loan.loan_id, loan.emi))
            charge = min(savings, P.BOUNCE_CHARGE)
            savings -= charge
            record.charges += charge

    cushion = scale(b.base_income, 0.2)
    for loan in sorted(b.loans, key=lambda loan: loan.loan_id):
        if loan.written_off or loan.arrears(month) == 0:
            continue
        if savings >= loan.emi + cushion and rng.random() < 0.3 + 0.6 * disc:
            savings -= loan.emi
            loan.paid += 1
            paid_total += loan.emi
            record.payments.append(Payment(loan.loan_id, loan.emi, manual=True))

    # Organic new credit: a lender approves only while debt stays under its cap.
    if organic_credit and rng.random() < 0.012 * P.SEGMENTS[b.segment]["access"]:
        kind = pick(rng, P.SEGMENTS[b.segment]["kinds"])
        st.loan_counter += 1
        loan = new_loan(rng, b.borrower_id, st.loan_counter, kind, b.base_income, month)
        current = sum(x.emi for x in b.loans if x.is_open(month) and not x.written_off)
        if b.stacker or current + loan.emi <= scale(b.base_income, 0.5):
            b.loans.append(loan)
            if loan.reported:
                b.enquiries.append(month)
            if b.credit_history_start is None and loan.reported:
                b.credit_history_start = month

    flow = income - essentials_paid - paid_total - record.charges
    save_rate = b.save_rate
    target_buffer = scale(b.base_income, 1.0 + 2.0 * disc)
    if b.segment == "smallholder_farmer":
        target_buffer = scale(b.base_income, 3.0 + 4.0 * disc)   # harvest cash must last
        if income > b.base_income:
            save_rate = min(0.95, 0.55 + 0.4 * disc)
    spend = scale(max(0, flow - windfall), 1.0 - save_rate)
    spend += scale(max(0, savings - target_buffer), 0.15)
    if windfall and b.traits:
        spend += scale(windfall, 0.3 + 0.6 * b.traits.present_bias)   # present bias spends a windfall now
    record.discretionary = min(spend, savings)
    savings -= record.discretionary

    for loan in b.loans:
        if loan.written_off or month < loan.start:
            continue
        arrears = loan.arrears(month)
        if arrears >= P.WRITE_OFF_ARREARS and not loan.written_off:
            loan.written_off = True
            loan.written_off_month = month
        if loan.is_open(month) or loan.written_off:
            loan.grid[month] = min(arrears * 30, P.DPD_CAP)

    st.savings = savings
    st.behind = st.behind + 1 if record.bounces else 0
    record.savings_end = savings
    return record


def simulate(b: Borrower, rng: random.Random, new: Loan,
             aux: random.Random | None = None) -> tuple[list[MonthTrue], list[MonthTrue]]:
    """Run the 24 history months, disburse the applied-for loan, then the performance months.

    Returns (history, performance). Performance covers the application month and the 12 months
    in which the new loan's first 12 EMIs fall due.
    """
    st = SimState(savings=b.savings, loan_counter=len(b.loans) + 1,
                  aux=aux or random.Random(f"{P.SEED}:{b.borrower_id}:aux"))
    history = [run_month(b, m, rng, st, organic_credit=True)
               for m in range(b.app_month - P.HISTORY_MONTHS, b.app_month)]
    b.loans.append(new)
    performance = [run_month(b, m, rng, st, organic_credit=False)
                   for m in range(b.app_month, b.app_month + P.PERFORMANCE_MONTHS + 1)]
    return history, performance
