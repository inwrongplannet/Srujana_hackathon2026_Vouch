"""Stage 3: what a lender actually sees. This is where gaps, errors and lies enter.

Each source is either observed or carries a reason code (see params.STATUSES):
- bank statement: linked or NOT_PROVIDED; full or PARTIAL; may contain window dressing,
  round-tripping or duplicated rows from a bad import.
- bureau: exists only if the borrower ever had reported credit, otherwise NO_RECORD.
  Unreported digital loans never show up; lenders sometimes skip a month (XXX).
- declared income: honest, inflated, or WITHHELD (more likely when income is low or erratic).
- declared EMIs: stackers leave their app loans off; honest people sometimes forget one.
- GST: only registered kirana businesses file; some months are missed.
"""

import random
from dataclasses import dataclass, field
from statistics import median

from . import params as P
from .model import Borrower, Loan, month_label
from .money import outstanding, round_to, rupees, scale
from .simulate import MonthTrue



@dataclass
class BankMonth:
    """One month of the bank-statement view. Credits and debits are itemised lines in paise."""

    month: int
    opening: int
    income_lines: list[int] = field(default_factory=list)
    passthrough: int = 0                  # kirana sales collected then paid to suppliers
    cash_deposit: int = 0
    disbursals: list[tuple[str, int]] = field(default_factory=list)
    loan_debits: list[tuple[str, int, bool]] = field(default_factory=list)   # (loan, amount, manual)
    returns: list[tuple[str, int]] = field(default_factory=list)              # bounced auto-debits
    charges: int = 0
    spend: int = 0
    atm: int = 0
    window_dressing: int = 0
    round_trip: int = 0
    duplicate_credit: int = 0             # parse error: a credit line counted twice
    closing: int = 0

    def credits(self) -> int:
        return (sum(self.income_lines) + self.passthrough + self.cash_deposit
                + sum(a for _, a in self.disbursals) + self.window_dressing + self.round_trip
                + self.duplicate_credit)

    def debits(self) -> int:
        return (sum(a for _, a, _ in self.loan_debits) + self.charges + self.spend + self.atm
                + self.passthrough + self.round_trip)


def split_income(b: Borrower, amount: int, rng: random.Random) -> list[int]:
    """Break a month's banked income into the credit lines its segment typically produces."""
    if amount <= 0:
        return []
    if b.segment in ("salaried_formal", "pension"):
        return [amount]
    pieces = {"gig_platform": (8, 20), "kirana_msme": (15, 30),
              "smallholder_farmer": (1, 3), "informal_daily_wage": (3, 6)}[b.segment]
    count = max(1, min(rng.randint(*pieces), amount // 10_000))   # no line below ₹100
    weights = [rng.random() + 0.2 for _ in range(count)]
    total = sum(weights)
    lines = [scale(amount, w / total) for w in weights]
    lines[-1] += amount - sum(lines)      # last line absorbs rounding so the month reconciles
    return [line for line in lines if line > 0]


def bank_view(b: Borrower, history: list[MonthTrue], months: int, rng: random.Random) -> list[BankMonth]:
    """Statement months (most recent `months` before the application), reconciled to the paisa."""
    share = b.deposit_share
    window = history[-months:]
    previous_savings = history[-months - 1].savings_end if len(history) > months else b.savings
    balance = scale(previous_savings, share)
    out: list[BankMonth] = []
    duplicate_month = rng.randrange(len(window)) if b.duplicate_import else -1
    for i, t in enumerate(window):
        bm = BankMonth(month=t.month, opening=balance)
        bm.income_lines = split_income(b, scale(t.income, share), rng)
        if b.segment == "kirana_msme":
            turnover = scale(t.income, 1.0 / b.margin)
            bm.passthrough = scale(turnover - t.income, share)
        bm.disbursals = list(t.disbursals)
        bm.loan_debits = [(p.loan_id, p.amount, p.manual) for p in t.payments]
        bm.returns = list(t.bounces)
        bm.charges = t.charges
        bm.spend = scale(t.essentials + t.discretionary, share)
        target = scale(t.savings_end, share)
        # Cash that moves between pocket and bank closes the gap to the true balance.
        residual = balance + bm.credits() - bm.debits() - target
        if residual > 0:
            bm.atm = residual
        else:
            bm.cash_deposit = -residual
        if b.round_tripper and rng.random() < 0.5:
            bm.round_trip = round_to(scale(sum(bm.income_lines) + bm.passthrough, rng.uniform(0.5, 1.5)), rupees(1000))
        if b.window_dresser and i == len(window) - 1:
            bm.window_dressing = round_to(scale(b.base_income, rng.uniform(1.5, 3.0)), rupees(1000))
        bm.closing = balance + bm.credits() - bm.debits()
        if i == duplicate_month and bm.income_lines:
            bm.duplicate_credit = rng.choice(bm.income_lines)   # closing balance stays true
        balance = target
        out.append(bm)
    return out


def bureau_view(b: Borrower, app_month: int, rng: random.Random) -> list[dict]:
    """Tradelines a bureau would return at the application date; [] means NO_RECORD."""
    rows: list[dict] = []
    window = range(app_month - P.HISTORY_MONTHS, app_month)
    for loan in sorted(b.loans, key=lambda x: x.loan_id):
        if loan.is_new or not loan.reported or loan.start >= app_month:
            continue
        cells = []
        for m in window:
            if m not in loan.grid:
                cells.append(P.GRID_NOT_OPEN)
            elif rng.random() < P.P_GRID_GAP:
                cells.append(P.GRID_NOT_REPORTED)
            else:
                cells.append(f"{loan.grid.get(m, 0):03d}")
        last = app_month - 1
        if loan.written_off:
            status = "WRITTEN_OFF"
        elif loan.is_open(last):
            status = "ACTIVE"
        else:
            status = "CLOSED"
        rows.append({
            "tradeline_id": loan.loan_id, "lender_type": loan.lender_type, "loan_kind": loan.kind,
            "opened_month": month_label(loan.start), "sanctioned_minor": loan.principal,
            "emi_minor": loan.emi, "tenure_months": loan.tenure, "status": status,
            "outstanding_minor": 0 if status == "CLOSED" else outstanding(loan.principal, loan.rate, loan.tenure, loan.paid),
            "dpd_grid": "|".join(cells),
        })
    for n in range(b.prior_closed_loans):
        rows.append({
            "tradeline_id": f"{b.borrower_id}-P{n + 1:02d}", "lender_type": rng.choice(("BANK", "NBFC", "MFI")),
            "loan_kind": "closed_prior", "opened_month": month_label(b.credit_history_start + 3 * n),
            "sanctioned_minor": round_to(scale(b.base_income, rng.uniform(1.0, 5.0)), rupees(500)),
            "emi_minor": 0, "tenure_months": 0, "status": "CLOSED", "outstanding_minor": 0,
            "dpd_grid": "|".join([P.GRID_NOT_OPEN] * P.HISTORY_MONTHS),
        })
    return rows


def declared_view(b: Borrower, history: list[MonthTrue], rng: random.Random) -> dict:
    """The application form: income, EMIs and occupation tenure as the applicant states them."""
    recent = [t.income for t in history[-P.STATEMENT_MONTHS:]]
    true_median = int(median(recent)) if recent else b.base_income
    withhold = 0.04 + (0.10 if b.cv > 0.15 else 0.0) + (0.06 if b.base_income < rupees(15_000) else 0.0)
    if rng.random() < withhold:
        income, income_status = None, P.WITHHELD
    else:
        factor = rng.uniform(1.3, 1.8) if b.inflator else rng.uniform(0.9, 1.1)
        income, income_status = round_to(scale(max(true_median, b.base_income // 2), factor), rupees(1000)), P.OBSERVED

    open_loans = [loan for loan in b.loans
                  if not loan.is_new and not loan.written_off and loan.is_open(b.app_month - 1)]
    forget = rng.random() < P.P_UNDISCLOSED_LOAN
    declared_emi = 0
    for loan in sorted(open_loans, key=lambda x: x.emi):
        hidden = (b.stacker and loan.lender_type == "FINTECH") or forget
        if hidden:
            loan.declared = False
            forget = False
            continue
        declared_emi += loan.emi
    tenure = None if rng.random() < P.P_TENURE_MISSING else b.tenure_months
    return {
        "declared_income_minor": income, "declared_income_status": income_status,
        "declared_emi_minor": declared_emi, "declared_emi_status": P.OBSERVED,
        "occupation_tenure_months": tenure,
        "occupation_tenure_status": P.OBSERVED if tenure is not None else P.NOT_PROVIDED,
    }


def gst_view(b: Borrower, history: list[MonthTrue], rng: random.Random) -> list[dict]:
    """GSTR-style monthly turnover filings for registered kirana businesses; [] otherwise."""
    if not b.gst_registered:
        return []
    rows = []
    for t in history[-P.STATEMENT_MONTHS:]:
        if rng.random() < P.P_GST_MISSED:
            rows.append({"month": month_label(t.month), "status": "MISSED", "turnover_minor": None})
        else:
            turnover = scale(t.income, b.gst_underreport / b.margin)
            rows.append({"month": month_label(t.month), "status": "FILED", "turnover_minor": round_to(turnover, rupees(100))})
    return rows


def statement_months(b: Borrower, rng: random.Random) -> tuple[int, str]:
    """How many statement months the applicant shares, and the matching status."""
    seg = P.SEGMENTS[b.segment]
    p_link = seg["p_link"] * (1.1 if b.urban else 0.8) * (1.1 if b.age_band in ("21-25", "26-35") else 0.9)
    if rng.random() >= min(0.97, p_link):
        return 0, P.NOT_PROVIDED
    if rng.random() < P.P_FULL_STATEMENT:
        return P.STATEMENT_MONTHS, P.OBSERVED
    return rng.choice(P.PARTIAL_STATEMENT_MONTHS), P.PARTIAL


def existing_emi_true(b: Borrower) -> int:
    """True EMI load at the application date: every open, not written-off loan."""
    return sum(loan.emi for loan in b.loans
               if not loan.is_new and not loan.written_off and loan.is_open(b.app_month - 1)
               and loan.start + loan.tenure >= b.app_month)


def loan_is_undeclared(loan: Loan) -> bool:
    return not loan.is_new and not loan.declared
