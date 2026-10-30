"""``shop-data generate``: write the raw parquet extracts that the dbt sources read."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from shop_data.generator import GeneratorConfig, generate
from shop_data.writer import write_parquet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shop-data", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate", help="simulate the shop and write raw extracts")
    g.add_argument("--out", type=Path, default=Path("data/raw"))
    g.add_argument("--seed", type=int, default=GeneratorConfig.seed)
    g.add_argument("--customers", type=int, default=GeneratorConfig.n_customers)
    g.add_argument("--products", type=int, default=GeneratorConfig.n_products)
    g.add_argument(
        "--as-of",
        type=datetime.fromisoformat,
        help="extract the state at this time (default: end of the simulated period)",
    )
    args = parser.parse_args(argv)

    cfg = replace(
        GeneratorConfig(), seed=args.seed, n_customers=args.customers, n_products=args.products
    )
    raw = generate(cfg, as_of=args.as_of)
    counts = write_parquet(raw, args.out)
    as_of = args.as_of or cfg.end
    print(f"raw extracts as of {as_of:%Y-%m-%d %H:%M} -> {args.out}/")
    for name, n in counts.items():
        print(f"  {name:<12} {n:>9,} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
