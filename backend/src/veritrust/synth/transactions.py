"""Stage 4: turn a statement month into line items, and read line items back into a month.

`to_transactions` writes narrations the way Indian bank statements look (NEFT, UPI, NACH, ATM).
`extract_months` is the cash-flow extractor: it only reads narrations and amounts, the same way
it would read a real Account Aggregator statement. A test checks that extracting the generated
lines reproduces the monthly table exactly. All names are fictional.
"""

import calendar
import random
import re
from collections import OrderedDict

from .model import Borrower, Loan, year_month
from .money import scale
from .observe import BankMonth

EMPLOYERS = ("ARUNODAY SYSTEMS", "VEDIKA TEXTILES", "PRAGATI LOGISTICS", "NAVYUG PHARMA")
PLATFORMS = ("ZOOMRIDE", "DABBAGO", "SWIFTDROP")
SHOPS = ("SHREE KIRANA", "ANNAPURNA STORES", "OM SUPERMART", "GANESH PROVISIONS", "LAXMI DAIRY")
WHOLESALERS = ("MAHALAXMI TRADERS", "BHARAT DISTRIBUTORS", "SURYA AGENCIES")
PEOPLE = ("R KUMAR", "S DEVI", "A PATIL", "M REDDY", "K SINGH")
FIRMS = ("M/S JAI AMBE ENTERPRISES", "M/S NEELKANTH TRADING")
MANDIS = ("APMC MANDI GADAG", "APMC MANDI LATUR", "KRISHI UPAJ SAMITI")

EMI_DEBIT = re.compile(r"^(NACH DR|UPI DR .* OVERDUE)")
RETURN_CHARGE = re.compile(r"^NACH RTN CHG")
DISBURSAL = re.compile(r"LOAN DISB")


def _split(amount: int, count: int, rng: random.Random) -> list[int]:
    if amount <= 0:
        return []
    count = max(1, min(count, amount // 100))   # keep every part at least ₹1
    weights = [rng.random() + 0.3 for _ in range(count)]
    total = sum(weights)
    parts = [scale(amount, w / total) for w in weights]
    parts[-1] += amount - sum(parts)
    return [p for p in parts if p > 0]


def _credit_narration(b: Borrower, rng: random.Random, big: bool) -> str:
    if b.segment == "salaried_formal":
        return f"NEFT CR SAL {EMPLOYERS[int(b.borrower_id[1:]) % len(EMPLOYERS)]}"
    if b.segment == "pension":
        return "NEFT CR PENSION CREDIT"
    if b.segment == "gig_platform":
        return f"UPI CR {rng.choice(PLATFORMS)} PAYOUT"
    if b.segment == "kirana_msme":
        return f"UPI CR {rng.randint(70000, 99999)}@okbank COLLECT"
    if b.segment == "smallholder_farmer":
        return f"NEFT CR {rng.choice(MANDIS)}" if big else "UPI CR LABOUR PAYMENT"
    return f"UPI CR CONTRACTOR {rng.choice(PEOPLE)}" if rng.random() < 0.5 else "CASH DEP SELF CDM"


def to_transactions(b: Borrower, bm: BankMonth, loans: dict[str, Loan], rng: random.Random,
                    counter: list[int]) -> list[dict]:
    """Line items for one statement month. The running balance never goes below zero."""
    year, month = year_month(bm.month)
    days = calendar.monthrange(year, month)[1]
    credits: list[tuple[int, str, int]] = []
    debits: list[tuple[int, str, int]] = []
    returns: list[tuple[int, str, int]] = []

    big_cut = scale(b.base_income, 1.5)
    for amount in bm.income_lines:
        day = 1 if b.segment in ("salaried_formal", "pension") else rng.randint(1, days)
        credits.append((day, _credit_narration(b, rng, amount > big_cut), amount))
    if bm.passthrough:
        for amount in _split(bm.passthrough, rng.randint(15, 30), rng):
            credits.append((rng.randint(1, days), _credit_narration(b, rng, False), amount))
    for loan_id, amount in bm.disbursals:
        credits.append((rng.randint(1, days), f"NEFT CR {loans[loan_id].lender} LOAN DISB {loan_id}", amount))
    if bm.cash_deposit:
        credits.append((rng.randint(1, min(days, 9)), "CASH DEP SELF BRANCH", bm.cash_deposit))
    if bm.window_dressing:
        credits.append((rng.randint(26, days), f"IMPS CR {rng.choice(PEOPLE)}", bm.window_dressing))
    if bm.round_trip:
        firm, day = rng.choice(FIRMS), rng.randint(3, days - 2)
        credits.append((day, f"IMPS CR {firm}", bm.round_trip))
        debits.append((day + 1, f"IMPS DR {firm}", bm.round_trip))

    for loan_id, amount, manual in bm.loan_debits:
        loan = loans[loan_id]
        if manual:
            debits.append((rng.randint(15, days), f"UPI DR {loan.lender} OVERDUE {loan_id}", amount))
        else:
            debits.append((loan.emi_day, f"NACH DR {loan.lender} {loan_id}", amount))
    charge_parts = _split(bm.charges, len(bm.returns), rng) if bm.returns else []
    for i, (loan_id, amount) in enumerate(bm.returns):
        loan = loans[loan_id]
        returns.append((loan.emi_day, f"NACH RTN INSUFFICIENT FUNDS {loan.lender} {loan_id}", amount))
        if i < len(charge_parts):
            debits.append((loan.emi_day, f"NACH RTN CHG {loan_id}", charge_parts[i]))
    if bm.passthrough:
        for amount in _split(bm.passthrough, rng.randint(2, 5), rng):
            debits.append((rng.randint(1, days), f"NEFT DR {rng.choice(WHOLESALERS)} SUPPLIES", amount))

    spend = bm.spend
    if spend:
        rent = scale(spend, 0.25) if b.urban and b.segment != "smallholder_farmer" else 0
        power = scale(spend, 0.04)
        phone = scale(spend, 0.01)
        groceries = spend - rent - power - phone
        if rent:
            debits.append((rng.randint(1, 5), "IMPS DR RENT", rent))
        debits.append((rng.randint(5, 20), "BBPS DR ELECTRICITY BILL", power))
        debits.append((rng.randint(1, days), "UPI DR MOBILE RECHARGE", phone))
        for amount in _split(groceries, rng.randint(6, 18), rng):
            debits.append((rng.randint(1, days), f"UPI DR {rng.choice(SHOPS)}", amount))
    for amount in _split(bm.atm, rng.randint(1, 4), rng):
        debits.append((rng.randint(1, days), "ATM WDL CASH", amount))

    credits.sort(key=lambda x: (x[0], x[1], x[2]))
    debits.sort(key=lambda x: (x[0], x[1], x[2]))
    returns.sort(key=lambda x: (x[0], x[1], x[2]))
    rows: list[dict] = []
    balance = bm.opening

    def emit(day: int, narration: str, kind: str, amount: int, balance_after: int) -> None:
        counter[0] += 1
        rows.append({"borrower_id": b.borrower_id, "txn_id": f"{b.borrower_id}-T{counter[0]:05d}",
                     "date": f"{year:04d}-{month:02d}-{day:02d}", "narration": narration,
                     "txn_type": kind, "amount_minor": amount, "balance_minor": balance_after})

    duplicate_left = bm.duplicate_credit
    pending = list(debits)
    for day in range(1, days + 1):
        for d, narration, amount in (c for c in credits if c[0] == day):
            balance += amount
            emit(day, narration, "CREDIT", amount, balance)
            if duplicate_left and amount == duplicate_left:
                emit(day, narration, "CREDIT", amount, balance)   # parse duplicate: balance repeats
                duplicate_left = 0
        for d, narration, amount in (r for r in returns if r[0] == day):
            emit(day, narration, "RETURN", amount, balance)
        still = []
        for d, narration, amount in pending:
            if d <= day and (balance >= amount or day == days):
                balance -= amount
                emit(day, narration, "DEBIT", amount, balance)
            else:
                still.append((d, narration, amount))
        pending = still
    return rows


def extract_months(rows: list[dict]) -> "OrderedDict[str, dict]":
    """Monthly cash-flow summary read only from narrations and amounts, keyed by 'YYYY-MM'."""
    months: "OrderedDict[str, dict]" = OrderedDict()
    for row in rows:
        key = row["date"][:7]
        m = months.setdefault(key, {
            "credits_minor": 0, "debits_minor": 0, "emi_debits_minor": 0, "emi_bounces": 0,
            "bounce_charges_minor": 0, "disbursal_credits_minor": 0, "disbursal_count": 0,
            "opening_balance_minor": None, "closing_balance_minor": 0,
        })
        amount, kind = row["amount_minor"], row["txn_type"]
        if m["opening_balance_minor"] is None:
            signed = amount if kind == "CREDIT" else -amount if kind == "DEBIT" else 0
            m["opening_balance_minor"] = row["balance_minor"] - signed
        if kind == "CREDIT":
            m["credits_minor"] += amount
            if DISBURSAL.search(row["narration"]):
                m["disbursal_credits_minor"] += amount
                m["disbursal_count"] += 1
        elif kind == "DEBIT":
            m["debits_minor"] += amount
            if EMI_DEBIT.match(row["narration"]):
                m["emi_debits_minor"] += amount
            elif RETURN_CHARGE.match(row["narration"]):
                m["bounce_charges_minor"] += amount
        else:
            m["emi_bounces"] += 1
        m["closing_balance_minor"] = row["balance_minor"]
    return months
