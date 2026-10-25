"""A month-by-month delinquency trajectory for real applicants, from their real bureau grids.

Home Credit publishes no bureau score, so none is invented here (score_status is always
NO_SCORE_AVAILABLE). What the 24-cell payment grids do show, month by month, is how far behind
the person was on any reported line, how many lines were reporting, and when new lines opened.
That is the real before/after a lender sees when a borrower's record suddenly worsens.
"""

from veritrust.synth import params as P


def _index(label: str) -> int:
    return int(label[:4]) * 12 + int(label[5:]) - 1


def _label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def trajectory_rows(borrower_id: str, application_month: str, tradelines: list[dict]) -> list[dict]:
    """24 rows, oldest first, ending the month before the application."""
    app = _index(application_month)
    worst: list[int | None] = []
    rows = []
    for k in range(P.HISTORY_MONTHS):
        month = app - P.HISTORY_MONTHS + k
        cells = [t["dpd_grid"].split("|")[k] for t in tradelines]
        numeric = [int(c) for c in cells if c.isdigit()]
        now = max(numeric) if numeric else None
        worst.append(now)
        window = [w for w in worst[-24:] if w is not None]
        before = worst[k - 3] if k >= 3 else None
        rows.append({
            "borrower_id": borrower_id, "snapshot_month": _label(month),
            "worst_dpd_reported": "" if now is None else now,
            "reporting_tradelines": len(numeric),
            "not_reported_cells": sum(1 for c in cells if c == P.GRID_NOT_REPORTED),
            "months_30plus_rolling": sum(1 for w in window if w >= 30),
            "new_tradelines_6m": sum(1 for t in tradelines if month - 6 < _index(t["opened_month"]) <= month),
            "delinquency_spike": int(now is not None and before is not None and now >= 30 > before),
            "score_status": "NO_SCORE_AVAILABLE",
        })
    return rows
