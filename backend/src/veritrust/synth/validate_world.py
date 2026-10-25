"""Does the simulated world behave like the real one? Targets from published outcomes, not tuned to.

Run: python -m veritrust.synth.validate_world --data ../data/synth [--peer-sample 600]
Writes world_validation.json. Each check reports its number beside the published target and a
PASS or MISS; a MISS is a known gap, written up in data/combined/README.md, never hidden.

Months are whole months: one unpaid EMI at month end is 1-29 real days late, so real-world PAR30 is
two or more unpaid EMIs (grid >= 60 days) and PAR90 is four or more (grid >= 120).
"""

import argparse
import copy
import csv
import json
from collections import defaultdict
from pathlib import Path

from . import params as P
from .world import pandemic_chance


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _month(label: str) -> int:
    year, month = label.split("-")
    return int(year) * 12 + int(month) - 1


def _share(rows, cond, threshold: int) -> tuple[float | None, int]:
    hits = total = 0
    for borrower, r in rows:
        if r["status"] in ("SETTLED", "CHARGED_OFF") or not cond(borrower, _month(r["calendar_month"])):
            continue
        total += 1
        hits += int(r["dpd_days"]) >= threshold
    return (hits / total if total else None), total


def _check(name: str, value: float | None, low: float, high: float, n: int, source: str) -> dict:
    ok = value is not None and low <= value <= high
    return {"check": name, "value": None if value is None else round(value, 4), "target": [low, high],
            "n": n, "result": "PASS" if ok else "MISS", "source": source}


def peer_effect(sample: int) -> float:
    """Structural Breza check: the same borrowers with every peer current vs every peer behind."""
    from .generate import _outcome, _prepare
    from .simulate import SimState, run_month
    from .vouch import VoucherPool
    from .world import build_worlds

    worlds, pool = build_worlds(), VoucherPool()
    preps = [_prepare(i, pool, "main", worlds) for i in range(1, sample + 1)]

    def rate(share: float) -> float:
        hits = 0
        for prep in preps:
            p = copy.deepcopy(prep)
            b, rng, new = p["b"], p["rng"], p["new"]
            st = SimState(savings=b.savings, loan_counter=len(b.loans) + 1, aux=p["aux"])
            for m in range(b.app_month - P.HISTORY_MONTHS, b.app_month + P.PERFORMANCE_MONTHS + 1):
                if m == b.app_month:
                    b.loans.append(new)
                run_month(b, m, rng, st, organic_credit=m < b.app_month, peer_share=share if m >= b.app_month else 0.0)
            hits += _outcome(b, new)["default_12m"]
        return hits / len(preps)

    return rate(1.0) - rate(0.0)


def validate(data: Path, peer_sample: int = 600) -> dict:
    apps = {r["borrower_id"]: r for r in _read(data / "applications.csv") if r["cohort"] == "main"}
    truth = {r["borrower_id"]: r for r in _read(data / "truth.csv") if r["borrower_id"] in apps}
    perf = [(r["borrower_id"], r) for r in _read(data / "loan_performance.csv") if r["borrower_id"] in apps]
    floods = defaultdict(set)
    for r in _read(data / "life_events.csv"):
        if r["borrower_id"] in apps and r["event"] == "FLOOD":
            floods[r["borrower_id"]].add(_month(r["month"]))
    onset = {b: _month(t["world_pandemic_onset"]) for b, t in truth.items() if t["world_pandemic_onset"]}
    approved = {b for b, a in apps.items() if a["legacy_decision"] == "APPROVE"}
    normal = [x for x in perf if x[0] not in onset]
    pandemic = [x for x in perf if x[0] in onset]
    after = lambda b, m: 6 <= m - onset[b] <= 12

    checks = []
    v, n = _share([x for x in normal if x[0] in approved], lambda b, m: True, 60)
    checks.append(_check("PAR30, normal worlds, loans a bureau-only lender approves", v, 0.015, 0.035, n,
                         "Crisil, 12 Apr 2021: microfinance PAR30 about 2.5% in Dec 2019"))
    v, n = _share(pandemic, after, 60)
    checks.append(_check("PAR30, 6-12 months into a pandemic, all applicants", v, 0.11, 0.15, n,
                         "Crisil: about 11% (Dec 2020); CRIF High Mark: 15% (Apr-Jun 2021)"))
    v, n = _share(pandemic, after, 120)
    checks.append(_check("PAR90, 6-12 months into a pandemic, all applicants", v, 0.033, 0.044, n,
                         "CRIF High Mark, Dec 2021: 90+ DPD 4.4% (Mar 2021) and 3.3% (Sep 2021)"))
    v, n = _share([x for x in pandemic if x[0] in approved], after, 60)
    checks.append(_check("PAR30, 6-12 months into a pandemic, approved loans", v, 0.11, 0.15, n, "as above"))

    flooded = [x for x in perf if floods[x[0]]]
    hit, n_hit = _share(flooded, lambda b, m: any(0 <= m - f <= 1 for f in floods[b]), 30)
    later, n_later = _share(flooded, lambda b, m: any(3 <= m - f <= 4 for f in floods[b]), 30)
    base, _ = _share(normal, lambda b, m: True, 30)
    ratio = hit / base if hit is not None and base else None
    checks.append(_check("Flood: late EMIs in the flood month and the next, x normal rate", ratio, 2.0, 20.0, n_hit,
                         "RBI Bulletin 2020, Chart 5: Kerala PAR 1-30 44% vs 3% for India (Sep 2018)"))
    recovery = later / hit if later is not None and hit else None
    checks.append(_check("Flood: late EMIs 3-4 months later, as a share of the peak", recovery, 0.0, 0.75, n_later,
                         "World Bank blog (Northern Arc pools): collections back within 1-2 months"))

    weighted = sum(float(apps[b]["world_weight"]) for b in onset) / sum(float(a["world_weight"]) for a in apps.values())
    checks.append(_check("Weighted share of borrowers in a pandemic world = real chance", weighted,
                         pandemic_chance() * 0.8, pandemic_chance() * 1.2, len(apps),
                         "Marani et al. 2021: one COVID-scale pandemic in about 59 years"))
    if peer_sample:
        gap = peer_effect(peer_sample)
        checks.append(_check("Peer effect: default, all peers behind minus all peers current", gap, 0.10, 0.15,
                             peer_sample, "Breza 2012: own repayment 10-15 points lower"))
    return {"checks": checks, "pandemic_chance": round(pandemic_chance(), 4)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=Path("../data/synth"))
    parser.add_argument("--peer-sample", type=int, default=600)
    args = parser.parse_args()
    report = validate(args.data, args.peer_sample)
    for c in report["checks"]:
        value = "-" if c["value"] is None else c["value"]
        print(f"{c['result']:4s}  {c['check']}: {value} (target {c['target'][0]}-{c['target'][1]}, n={c['n']})")
    (args.data / "world_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
