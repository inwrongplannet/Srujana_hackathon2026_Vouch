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
    events: list[tuple[str, str]] = field(default_factory=list)   # (category, name) from behaviour.py
    shock: str = ""
    lumpy: str = ""
    savings_end: int = 0


@dataclass
class SimState:
    savings: int
    harvest: dict = field(default_factory=dict)
    loan_counter: int = 0
    # Separate stream for the shock and vouch mechanics, so the original draws stay reproducible.
    aux: random.Random = field(default_factory=random.Random)
    behind: int = 0               # consecutive months with a bounced EMI


def _harvest_factor(b: Borrower, year: int, cal: int, rng: random.Random, st: SimState) -> float:
    season = ("kharif", year) if cal in (10, 11) else ("rabi", year)
    if season not in st.harvest:
        st.harvest[season] = lognormal(rng, 1.0, P.NOISE_HARVEST_SD)
    factor = st.harvest[season]
    traits = b.traits
    if season[0] == "kharif" and traits is not None and traits.world.drought(year):
        factor *= P.DROUGHT_CROP_FACTOR[traits.irrigated]
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
        amount = scale(base, days / 23 * (1.0 + rng.gauss(0.0, b.cv / 2)))

    # Personal job loss and hospital stays come from behaviour.step; here only the planned shock.
    shock = ""
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
    # ASSUMPTION: school fees in June for half of families with children. Medical bills and
    # one-off costs now come from behaviour.step (NSS hospital rates and NOISE).
    if cal == 6 and b.dependents and rng.random() < 0.5:
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
              organic_credit: bool, peer_share: float = 0.0) -> MonthTrue:
    """Simulate one month and update loans and savings in place.

    `peer_share` is the share of the borrower's neighbourhood group behind on an EMI last month.
    """
    plan = b.shock
    open_loans = [loan.loan_id for loan in b.loans if loan.is_open(month) and not loan.written_off]
    fx = step(b, b.traits, month, st.aux, open_loans) if b.traits else MonthEffects(discipline=b.discipline)
    disc = fx.discipline
    income, shock = income_for(b, month, rng, st)
    income = scale(income, fx.income_factor)
    essentials, lumpy = essentials_for(b, month, rng)
    essentials += fx.expense + scale(b.base_income, fx.extra_cost)
    if fx.savings_lost:
        st.savings -= scale(st.savings, fx.savings_lost)
    savings = st.savings + income
    if plan and month == plan.start:
        essentials += plan.expense
        lumpy = plan.kind.lower()
    shock = shock or fx.personal

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
                       shock=shock, lumpy=lumpy, events=fx.events)

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
        elif rng.random() < P.P_FAMILY_COVERS:
            record.informal_support = shortfall     # family or friends (Findex 2021); invisible to lenders
            savings += shortfall
    # Endorsers who stake their reputation also help, but only once trouble is visible: help
    # arrives the month after an EMI bounces, covering this month's dues and the arrears. So a
    # shock still reaches the bureau; the network decides how fast the borrower recovers. A
    # disaster that hit the borrower hits each endorser with the same exposure, and a hit endorser
    # cannot help this month.
    overdue = sum(loan.emi * loan.arrears(month - 1) for loan in b.loans if not loan.written_off)
    weight = 0.0
    if st.behind and savings < due_total + overdue:
        weight = sum(w for w in b.vouch_weight.get(month, []) if st.aux.random() >= fx.endorser_hit)
    if weight > 0 and st.aux.random() < 1.0 - math.exp(-weight):
        help_amount = min(due_total + overdue - savings, scale(b.base_income, P.VOUCH_SUPPORT_SHARE * weight))
        record.vouch_support = help_amount
        savings += help_amount

    if disc > 0.5:
        due.sort(key=lambda loan: (-(NEW_LOAN_PRIORITY if loan.is_new else PRIORITY[loan.kind]), loan.loan_id))
    else:
        rng.shuffle(due)
    paid_total = 0
    glitch_left = fx.glitch
    traits = b.traits
    for loan in due:
        # Peers behind on their EMIs pull repayment down (Breza; PEER_PULL in params.py).
        willful_skip = rng.random() < (1.0 - disc) * 0.05 + P.PEER_PULL * peer_share
        if loan.arrears(month - 1) >= 2 and disc < 0.5:
            willful_skip = willful_skip or rng.random() < 0.4   # disengages once behind
        glitch = glitch_left and savings >= loan.emi   # NOISE: the debit fails; money was there
        glitch_left = glitch_left and not glitch
        if (fx.moratorium and traits is not None and loan.loan_id in traits.moratorium_loans
                and (savings < loan.emi or willful_skip)):
            loan.start += 1                     # deferred: the whole schedule moves a month
            record.events.append(("COVARIATE", "MORATORIUM_DEFERRAL"))
            continue
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
    # Precautionary cash people keep before spending a surplus (ASSUMPTION, scaled by the
    # CALIBRATED BUFFER_SCALE).
    target_buffer = scale(b.base_income, P.BUFFER_SCALE * (1.0 + 2.0 * disc))
    if b.segment == "smallholder_farmer":
        target_buffer = scale(b.base_income, P.BUFFER_SCALE * (3.0 + 4.0 * disc))   # harvest cash must last
        if income > b.base_income:
            save_rate = min(0.95, 0.55 + 0.4 * disc)
    spend = scale(max(0, flow), 1.0 - save_rate)
    spend += scale(max(0, savings - target_buffer), 0.15)
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
    """Run one borrower alone (a neighbourhood group of one): history, then the new loan's months.

    Returns (history, performance). Performance covers the application month and the 12 months
    in which the new loan's first 12 EMIs fall due.
    """
    return simulate_group([(b, rng, new, aux)])[0]


def _arrears(b: Borrower, month: int) -> bool:
    return any(loan.arrears(month) > 0 for loan in b.loans if not loan.written_off and loan.is_open(month))


def simulate_group(members: list[tuple]) -> list[tuple[list[MonthTrue], list[MonthTrue]]]:
    """Simulate a neighbourhood group month by month, side by side.

    `members` holds (borrower, rng, new loan, aux rng). Each borrower lives their own window (24
    history months, then the new loan); in every calendar month each one sees the share of the
    other members who were behind on an EMI the month before (Breza's peer effect). A group of one
    reproduces the solo simulation.
    """
    states, spans = [], []
    for b, _, _, aux in members:
        states.append(SimState(savings=b.savings, loan_counter=len(b.loans) + 1,
                               aux=aux or random.Random(f"{P.SEED}:{b.borrower_id}:aux")))
        spans.append((b.app_month - P.HISTORY_MONTHS, b.app_month + P.PERFORMANCE_MONTHS))
    results: list[tuple[list[MonthTrue], list[MonthTrue]]] = [([], []) for _ in members]
    behind: dict[int, bool] = {}
    for month in range(min(s for s, _ in spans), max(e for _, e in spans) + 1):
        now: dict[int, bool] = {}
        for i, ((b, rng, new, _), st, (first, last)) in enumerate(zip(members, states, spans)):
            if not first <= month <= last:
                continue
            peers = [behind[j] for j in behind if j != i]
            share = sum(peers) / len(peers) if peers else 0.0
            if month == b.app_month:
                b.loans.append(new)
            record = run_month(b, month, rng, st, organic_credit=month < b.app_month, peer_share=share)
            results[i][0 if month < b.app_month else 1].append(record)
            now[i] = _arrears(b, month)
        behind = now
    return results
