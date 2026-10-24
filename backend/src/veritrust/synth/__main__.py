"""CLI: python -m veritrust.synth [--n 20000] [--out ../data/synth] [--transactions 300]."""

import argparse
from pathlib import Path

from .generate import generate


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic credit-assessment dataset.")
    parser.add_argument("--n", type=int, default=20_000, help="number of borrowers")
    parser.add_argument("--out", type=Path, default=Path("../data/synth"), help="output folder")
    parser.add_argument("--transactions", type=int, default=300,
                        help="borrowers that also get line-level bank statements")
    args = parser.parse_args()
    manifest = generate(args.n, args.out, args.transactions)
    for name, meta in manifest["files"].items():
        print(f"{name:24} {meta['rows']:>9} rows")


if __name__ == "__main__":
    main()
