"""Data shapes shared by the generator stages, plus month-index helpers.

Why: months are plain integers (year*12 + month-1) so windows are simple ranges.
"""

from dataclasses import dataclass, field
from decimal import Decimal


def month_index(year: int, month: int) -> int:
    """Month as one integer: year*12 + (month - 1)."""
    return year * 12 + month - 1


def year_month(index: int) -> tuple[int, int]:
    """Inverse of `month_index`."""
    return index // 12, index % 12 + 1


def month_label(index: int) -> str:
    """'YYYY-MM' for a month index."""
    year, month = year_month(index)
    return f"{year:04d}-{month:02d}"


@dataclass
class Loan:
    """One credit line. Disbursed in month `start`; EMIs fall due in start+1 .. start+tenure."""

    loan_id: str
    kind: str
    lender_type: str
    lender: str
    principal: int            # paise
    rate: Decimal             # annual fraction
    tenure: int               # months
    emi: int                  # paise
    start: int                # month index of disbursal
    emi_day: int
    reported: bool            # does the lender report to the bureau?
    declared: bool            # did the borrower list it on the application?
    is_new: bool = False      # the loan being applied for
    paid: int = 0             # instalments paid so far (on time or caught up)
    written_off: bool = False
    written_off_month: int | None = None
    grid: dict[int, int] = field(default_factory=dict)   # month -> days past due at month end

    def dues_by(self, month: int) -> int:
        """Instalments that have fallen due up to and including `month`."""
        return max(0, min(month - self.start, self.tenure))

    def arrears(self, month: int) -> int:
        """Unpaid instalments at the end of `month`."""
        return max(0, self.dues_by(month) - self.paid)

    def is_due(self, month: int) -> bool:
        return self.start < month <= self.start + self.tenure

    def is_open(self, month: int) -> bool:
        """Still on the books: inside its schedule, or past it with arrears left."""
        if self.written_off or month < self.start:
            return False
        return month <= self.start + self.tenure or self.arrears(month) > 0


@dataclass
class Borrower:
    """Hidden truth for one person. Only the observation layer decides what a lender sees."""

    borrower_id: str
    segment: str
    state: str
    urban: bool
    age_band: str
    dependents: int
    app_month: int
    base_income: int          # long-run monthly income, paise
    cv: float                 # month-to-month income noise
    expense_ratio: float      # essential spending as a share of long-run income
    discipline: float         # 0..1, how reliably they prioritise and pay dues
    save_rate: float          # share of surplus kept as savings
    deposit_share: float      # share of income and spending that passes through the bank
    margin: float             # kirana: net income / turnover; 1.0 for everyone else
    shock_prob: float
    shock_factor: float
    shock_max: int
    stacker: bool             # rolls shortfalls into new small digital loans
    inflator: bool            # overstates income on the application
    window_dresser: bool
    round_tripper: bool
    duplicate_import: bool
    gst_registered: bool
    gst_underreport: float
    community: bool
    macro_exposed: bool
    tenure_months: int        # months in current occupation
    savings: int              # liquid money at the start of the simulation, paise
    credit_history_start: int | None   # month of first bureau-reported credit, if any
    prior_closed_loans: int
    loans: list[Loan] = field(default_factory=list)
    bonus: bool = False
    # Depth of the person's community: how much help their endorsers could mobilise (0..1).
    support_capacity: float = 0.0
    enquiries: list[int] = field(default_factory=list)   # months a lender pulled the bureau file
    shock: "ShockPlan | None" = None
    vouch_weight: dict[int, float] = field(default_factory=dict)   # month -> total endorsement weight W


@dataclass
class ShockPlan:
    """One planned pre-application shock. Hidden truth: the lender only sees its traces."""

    kind: str                 # MEDICAL, JOB_LOSS, CROP, BUSINESS_DISRUPTION, FAMILY
    severity: int             # 1..3
    insured: bool
    start: int                # month index the shock begins
    months: int               # months income is depressed (income shocks); 1 for a one-off bill
    expense: int              # one-time cost in paise, after any insurance payout
    income_factor: float      # income multiplier while it lasts (1.0 for expense shocks)

    def active(self, month: int) -> bool:
        return self.start <= month < self.start + self.months
