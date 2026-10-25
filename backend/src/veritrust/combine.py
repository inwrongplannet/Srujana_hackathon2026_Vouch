"""Stack the simulated and anchored datasets into one dataset with the same tables.

python -m veritrust.combine [--synth ../data/synth] [--anchored ../data/anchored] [--prosper ../data/prosper]
                           [--out ../data/combined]

Every row gains `source` (real_anchored | simulated | real_prosper). Outcomes also carry `label_definition`,
and applications and features carry `recommended_use`: the two labels are defined differently,
so train and calibrate on one source at a time (real rows to fit, simulated rows to evaluate and
stress-test) rather than pooling them. The two answer keys (simulated truth, anchored injections)
become one `answer_key.csv`; it is never a model input. Columns a source lacks are left empty.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from veritrust.synth.generate import write_csv

SOURCES = {
    "real_anchored": {
        "label": "Home Credit TARGET: payment difficulties on the loan's early instalments",
        "use": "train_and_calibrate",
        "answer_key": "injections",
    },
    "simulated": {
        "label": "90+ days past due (3 unpaid EMIs) within the first 12 EMIs",
        "use": "evaluate_and_stress_test",
        "answer_key": "truth",
    },
    "real_prosper": {
        "label": "Prosper: charged off, defaulted or 120+ days past due, among resolved loans (column bad)",
        "use": "real_endorsement_check",
        "answer_key": None,
    },
}
TABLES = ("applications", "features", "outcomes", "monthly_cashflow", "bureau_tradelines", "gst_filings",
          "vouches", "transactions", "bureau_snapshots", "bureau_events", "vouch_events", "vouch_scores",
          "vouch_outcomes", "loan_performance", "shock_events", "life_events", "bureau_trajectory", "prosper_loans")


def _read(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _stack(parts: list[tuple[str, list[dict]]], extra) -> list[dict]:
    columns: list[str] = ["source"]
    for _, rows in parts:
        for key in (rows[0] if rows else {}):
            if key not in columns:
                columns.append(key)
    out = []
    for source, rows in parts:
        for row in rows:
            merged = {c: row.get(c, "") for c in columns}
            merged["source"] = source
            merged.update(extra(source))
            out.append(merged)
    return out


def combine(synth: Path, anchored: Path, out: Path, prosper: Path | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    folders = {"real_anchored": anchored, "simulated": synth}
    if prosper is not None and (prosper / "manifest.json").exists():
        folders["real_prosper"] = prosper
    files = {}
    for table in TABLES + ("answer_key",):
        parts = []
        for source, folder in folders.items():
            name = SOURCES[source]["answer_key"] if table == "answer_key" else table
            parts.append((source, _read(folder / f"{name}.csv") if name else []))

        def extra(source: str, table: str = table) -> dict:
            if table == "outcomes":
                return {"label_definition": SOURCES[source]["label"]}
            if table in ("applications", "features"):
                return {"recommended_use": SOURCES[source]["use"]}
            return {}

        rows = _stack(parts, extra)
        path = out / f"{table}.csv"
        write_csv(path, rows)
        files[f"{table}.csv"] = {
            "rows": len(rows),
            "rows_by_source": {s: len(r) for s, r in parts},
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    manifests = {s: json.loads((f / "manifest.json").read_text(encoding="utf-8")) for s, f in folders.items()}
    manifest = {
        "dataset": "combined",
        "sources": {s: {"label_definition": SOURCES[s]["label"], "recommended_use": SOURCES[s]["use"],
                        "borrowers": manifests[s]["borrowers"]} for s in folders},
        "money_unit": "integer paise (INR minor units); anchored amounts are Home Credit amounts rescaled",
        "warning": "Labels differ by source: fit and calibrate per source, never on the pooled rows.",
        "notice": "Contains real anonymised Home Credit and Prosper rows. Git-ignored; do not commit or share. Illustrative only, not financial advice.",
        "files": files,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine the simulated and anchored datasets.")
    parser.add_argument("--synth", type=Path, default=Path("../data/synth"))
    parser.add_argument("--anchored", type=Path, default=Path("../data/anchored"))
    parser.add_argument("--prosper", type=Path, default=Path("../data/prosper"))
    parser.add_argument("--out", type=Path, default=Path("../data/combined"))
    args = parser.parse_args()
    manifest = combine(args.synth, args.anchored, args.out, args.prosper)
    for name, meta in manifest["files"].items():
        by = "  ".join(f"{s} {n}" for s, n in meta["rows_by_source"].items() if n)
        print(f"{name:22} {meta['rows']:>9} rows  ({by})")


if __name__ == "__main__":
    main()
