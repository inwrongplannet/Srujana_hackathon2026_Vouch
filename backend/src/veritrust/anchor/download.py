"""Fetch the public source data into data/external/ (git-ignored; never committed).

python -m veritrust.anchor.download [--out ../data/external]

- Home Credit Default Risk: parquet mirror on Hugging Face, pinned to one revision so every
  teammate gets identical bytes. The original data is from a Kaggle competition; check its rules
  before any use beyond this prototype.
- Berka / PKDD'99 Czech bank: read from CTU's public MariaDB with the guest account the CTU page
  publishes (not a secret), saved as CSV.
"""

import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path

HF_REPO = "mohameddhameem/home-credit-default-risk"
HF_REVISION = "0c3a5ef31b39190ca2ac649d79b42c7f5b078227"
# POS_CASH_balance and credit_card_balance are skipped: bureau already carries debt and limits.
HF_TABLES = ("application_train_dated", "bureau", "bureau_balance", "installments_payments",
             "previous_application")

CTU = {"host": "relational.fel.cvut.cz", "port": 3306, "user": "guest", "password": "ctu-relational",
       "database": "financial"}
BERKA_TABLES = ("account", "trans", "loan", "district")


def _hf_files(table: str) -> list[str]:
    url = f"https://huggingface.co/api/datasets/{HF_REPO}/tree/{HF_REVISION}/{table}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return sorted(item["path"] for item in json.load(response) if item["path"].endswith(".parquet"))


def download_home_credit(out: Path) -> None:
    target = out / "home_credit"
    for table in HF_TABLES:
        for path in _hf_files(table):
            dest = target / path
            if dest.exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_REVISION}/{path}"
            tmp = dest.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(dest)
            print("home_credit", path)


def download_berka(out: Path) -> None:
    import pymysql   # only needed for this step; listed in requirements-data.txt

    target = out / "berka"
    target.mkdir(parents=True, exist_ok=True)

    def query(sql: str, args=()) -> tuple[list, list]:
        """Run one statement, reconnecting on dropped connections (the guest server drops them)."""
        for attempt in range(5):
            try:
                conn = pymysql.connect(connect_timeout=30, read_timeout=120, **CTU)
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql, args)
                        return [d[0] for d in cur.description], list(cur.fetchall())
                finally:
                    conn.close()
            except pymysql.err.OperationalError:
                if attempt == 4:
                    raise
                time.sleep(5 * (attempt + 1))
        raise RuntimeError("unreachable")

    for table in BERKA_TABLES:
        dest = target / f"{table}.csv"
        if dest.exists():
            continue
        tmp = dest.with_suffix(".part")
        if table != "trans":
            names, rows = query(f"SELECT * FROM `{table}`")
            with tmp.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(names)
                writer.writerows(rows)
        else:
            # The server caps statement time and sorting 1M rows exceeds it, so trans is read in
            # batches of 100 accounts through its account_id index. Each batch is written whole,
            # so an interrupted export resumes from the accounts already on disk.
            done: set[int] = set()
            has_header = tmp.exists() and tmp.stat().st_size > 0
            if has_header:
                with tmp.open(encoding="utf-8") as handle:
                    reader = csv.reader(handle)
                    column = next(reader).index("account_id")
                    done = {int(row[column]) for row in reader if row}
            _, ids = query("SELECT account_id FROM account ORDER BY account_id")
            todo = [row[0] for row in ids if row[0] not in done]
            with tmp.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                for i in range(0, len(todo), 100):
                    batch = todo[i:i + 100]
                    names, rows = query(f"SELECT * FROM trans WHERE account_id IN ({','.join(['%s'] * len(batch))})", batch)
                    if not has_header:
                        writer.writerow(names)
                        has_header = True
                    writer.writerows(rows)
                    handle.flush()
        tmp.rename(dest)
        print("berka", dest.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download public source datasets.")
    parser.add_argument("--out", type=Path, default=Path("../data/external"))
    parser.add_argument("--only", choices=("home_credit", "berka"))
    args = parser.parse_args()
    if args.only in (None, "berka"):
        download_berka(args.out)
    if args.only in (None, "home_credit"):
        download_home_credit(args.out)


if __name__ == "__main__":
    main()
