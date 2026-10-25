"""Stage 3b: a monthly bureau-style score and the events that moved it.

The score is an illustrative scorecard (params SCORE_*), 300-900, computed only from what the
simulated bureau sees: days past due, write-offs, utilisation of reported loans, enquiries and new
lines. It is never presented as a CIBIL or any real bureau's value. Every point it loses traces to
a `bureau_events` row, so "why did the score fall" always has a recorded answer.
"""

from decimal import ROUND_HALF_UP, Decimal

from . import params as P
from .model import Borrower, Loan, month_label
from .money import outstanding

R4 = Decimal("0.0001")
REASON = {"BUREAU_DELINQUENCY": "dpd", "WRITE_OFF": "write_off", "UTILISATION_SPIKE": "utilisation",
          "NEW_CREDIT_SEEKING": "enquiries", "OBLIGATION_INCREASE": "new_lines"}
EVENT_REASON = {"DPD_30": "BUREAU_DELINQUENCY", "DPD_60": "BUREAU_DELINQUENCY", "DPD_90": "BUREAU_DELINQUENCY",
                "WRITE_OFF": "WRITE_OFF", "UTILISATION_JUMP": "UTILISATION_SPIKE",
                "NEW_ENQUIRY": "NEW_CREDIT_SEEKING", "NEW_TRADELINE": "OBLIGATION_INCREASE"}


def _reported(b: Borrower) -> list[Loan]:
    return [loan for loan in b.loans if loan.reported and not loan.is_new]


def _dpd_points(dpd: int) -> int:
    return max((points for floor, points in P.SCORE_DPD_POINTS.items() if dpd >= floor), default=0)


def state_at(b: Borrower, month: int) -> dict | None:
    """What the bureau holds at the end of `month`; None when there is no file yet."""
    if b.credit_history_start is None or b.credit_history_start > month:
        return None
    loans = _reported(b)
    open_loans = [x for x in loans if month in x.grid and not (x.written_off_month is not None and x.written_off_month <= month)]
    worst = max((x.grid[month] for x in open_loans), default=0)
    late = sum(1 for m in range(month - 23, month + 1)
               if max((x.grid.get(m, 0) for x in loans), default=0) >= 30)
    max_dpd = max((x.grid.get(m, 0) for x in loans for m in range(month - 23, month + 1)), default=0)
    owed = sanctioned = 0
    for loan in open_loans:
        paid = max(0, loan.dues_by(month) - loan.grid[month] // 30)
        owed += outstanding(loan.principal, loan.rate, loan.tenure, paid)
        sanctioned += loan.principal
    utilisation = (Decimal(owed) / Decimal(sanctioned)).quantize(R4, rounding=ROUND_HALF_UP) if sanctioned else Decimal(0)
    return {
        "history": month - b.credit_history_start,
        "worst_dpd": worst,
        "late_months": late,
        "max_dpd_24m": max_dpd,
        "written_off": sum(1 for x in loans if x.written_off_month is not None and x.written_off_month <= month),
        "utilisation": utilisation,
        "enquiries_6m": sum(1 for e in b.enquiries if month - 6 < e <= month),
        "new_lines_6m": sum(1 for x in loans if month - 6 < x.start <= month),
        "active": len(open_loans),
        "outstanding": owed,
    }


def components(state: dict) -> dict[str, int]:
    """Points lost (negative) or earned per scorecard component."""
    excess = max(Decimal(0), state["utilisation"] - P.SCORE_UTILISATION_FREE)
    return {
        "history": min(state["history"], P.SCORE_HISTORY_MONTHS) * P.SCORE_HISTORY_POINTS // P.SCORE_HISTORY_MONTHS,
        "dpd": -_dpd_points(state["worst_dpd"]) - min(state["late_months"] * P.SCORE_PER_LATE_MONTH, P.SCORE_LATE_MONTHS_CAP),
        "write_off": -P.SCORE_WRITE_OFF_POINTS if state["written_off"] else 0,
        "utilisation": -int((excess * P.SCORE_UTILISATION_POINTS).quantize(Decimal(1), rounding=ROUND_HALF_UP)),
        "enquiries": -min(state["enquiries_6m"] * P.SCORE_PER_ENQUIRY, P.SCORE_ENQUIRY_CAP),
        "new_lines": -min(state["new_lines_6m"] * P.SCORE_PER_NEW_LINE, P.SCORE_NEW_LINE_CAP),
    }


def score(state: dict) -> int:
    low, high = P.SCORE_RANGE
    return max(low, min(high, P.SCORE_BASE + sum(components(state).values())))


def band(value: int) -> str:
    return next(name for ceiling, name in P.SCORE_BANDS if value < ceiling)


def snapshots(b: Borrower) -> list[dict]:
    """24 month-end snapshots ending the month before the application."""
    months = range(b.app_month - P.HISTORY_MONTHS, b.app_month)
    states = {m: state_at(b, m) for m in range(months[0] - 3, months[-1] + 1)}
    rows = []
    for m in months:
        st = states[m]
        if st is None:
            rows.append({"borrower_id": b.borrower_id, "snapshot_month": month_label(m), "bureau_score": "",
                         "score_band": "", "score_change_3m": "", "max_dpd_24m": "", "months_30plus_24m": "",
                         "active_tradelines": "", "total_outstanding_minor": "", "utilisation": "",
                         "enquiries_6m": "", "new_tradelines_6m": "", "written_off": "",
                         "snapshot_status": "NO_FILE", "top_reason_codes": "", "algorithm_version": P.SCORE_ALGORITHM})
            continue
        value = score(st)
        before = states.get(m - 3) if m - 3 >= months[0] else None   # no history before the window
        change = value - score(before) if before else ""
        reasons = ""
        if before:
            deltas = {code: components(st)[key] - components(before)[key] for code, key in REASON.items()}
            reasons = "|".join([code for code, d in sorted(deltas.items(), key=lambda kv: kv[1]) if d < 0][:3])
        rows.append({
            "borrower_id": b.borrower_id, "snapshot_month": month_label(m), "bureau_score": value,
            "score_band": band(value), "score_change_3m": change, "max_dpd_24m": st["max_dpd_24m"],
            "months_30plus_24m": st["late_months"], "active_tradelines": st["active"],
            "total_outstanding_minor": st["outstanding"], "utilisation": str(st["utilisation"]),
            "enquiries_6m": st["enquiries_6m"], "new_tradelines_6m": st["new_lines_6m"],
            "written_off": st["written_off"],
            "snapshot_status": "THIN_FILE" if st["history"] < P.THIN_FILE_MONTHS else P.OBSERVED,
            "top_reason_codes": reasons, "algorithm_version": P.SCORE_ALGORITHM,
        })
    return rows


def events(b: Borrower) -> list[dict]:
    """Adverse and credit-seeking events inside the 24-month window, with their point impact."""
    first, last = b.app_month - P.HISTORY_MONTHS, b.app_month - 1
    found: list[tuple[int, str, str, int]] = []   # (month, type, tradeline, points)
    for loan in _reported(b):
        for m in range(first, last + 1):
            if m not in loan.grid:
                continue
            prev, cur = loan.grid.get(m - 1, 0), loan.grid[m]
            crossed = [f for f in (90, 60, 30) if cur >= f > prev]
            if crossed:
                found.append((m, f"DPD_{crossed[0]}", loan.loan_id, _dpd_points(prev) - _dpd_points(cur)))
        if loan.written_off_month is not None and first <= loan.written_off_month <= last:
            found.append((loan.written_off_month, "WRITE_OFF", loan.loan_id, -P.SCORE_WRITE_OFF_POINTS))
        if first <= loan.start <= last:
            found.append((loan.start, "NEW_TRADELINE", loan.loan_id, -P.SCORE_PER_NEW_LINE))
    for e in b.enquiries:
        if first <= e <= last:
            found.append((e, "NEW_ENQUIRY", "", -P.SCORE_PER_ENQUIRY))
    for m in range(first, last + 1):
        now, before = state_at(b, m), state_at(b, m - 1)
        if now and before and now["utilisation"] - before["utilisation"] >= P.UTILISATION_JUMP:
            found.append((m, "UTILISATION_JUMP", "", components(now)["utilisation"] - components(before)["utilisation"]))
    found.sort(key=lambda x: (x[0], x[1], x[2]))
    return [{
        "event_id": f"{b.borrower_id}-E{n:03d}", "borrower_id": b.borrower_id, "event_month": month_label(m),
        "event_type": kind, "magnitude_points": points, "linked_tradeline_id": tradeline,
        "reason_code": EVENT_REASON[kind], "evidence_ref": f"bureau:{tradeline or b.borrower_id}:{month_label(m)}",
        "verified": 1,
    } for n, (m, kind, tradeline, points) in enumerate(found, start=1)]
