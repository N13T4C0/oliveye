"""CLI: monthly NDVI/NDMI for one municipality's olive-dominant cells, run locally.

Runs exactly the same code as the `openeo_monthly_indices` job of the CI queue, but on this
machine (interactive openEO login, local cache in data/cache/openeo).

Examples
--------
# 1. Inspect the request without contacting openEO (0 credits): cells, coverage, payload size.
uv run python scripts/extract_monthly_indices.py --province 23 --municipality 60 \
    --start 2025-07-01 --end 2025-08-01

# 2. Spend credits: one month for Martos.
uv run python scripts/extract_monthly_indices.py --province 23 --municipality 60 \
    --start 2025-07-01 --end 2025-08-01 --run
"""

from __future__ import annotations

import argparse
from pathlib import Path

from oliveye.jobs import JobContext, openeo_monthly_indices

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--province", required=True, help="INE province code, e.g. 23 (Jaén)")
    parser.add_argument("--municipality", required=True, help="SIGPAC municipality code, e.g. 60")
    parser.add_argument("--start", required=True, help="inclusive, first day of a month")
    parser.add_argument("--end", required=True, help="exclusive, first day of a month")
    parser.add_argument("--run", action="store_true", help="spend credits (default: dry run)")
    args = parser.parse_args()

    stem = f"{args.province}_{args.municipality}_{args.start}_{args.end}"
    ctx = JobContext(
        output_dir=REPO_ROOT / "data" / "interim" / f"indices_{stem}",
        openeo_cache_dir=REPO_ROOT / "data" / "cache" / "openeo",
        sigpac_dir=REPO_ROOT / "data" / "raw" / "sigpac",
    )
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    params = {
        "province": args.province,
        "municipality": args.municipality,
        "start": args.start,
        "end": args.end,
        "dry_run": not args.run,
    }
    for path in openeo_monthly_indices(params, ctx):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
