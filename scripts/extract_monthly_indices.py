"""CLI: monthly NDVI/NDMI of the olive area of one municipality, via one cached openEO batch job.

Examples
--------
# 1. Inspect the request without contacting openEO (0 credits): area, vertices, bbox.
uv run python scripts/extract_monthly_indices.py --province 23 --municipality 60 \
    --start 2025-07-01 --end 2025-08-01 --dry-run

# 2. Measure the cost of ONE month for Martos before scaling up.
uv run python scripts/extract_monthly_indices.py --province 23 --municipality 60 \
    --start 2025-07-01 --end 2025-08-01

# 3. A full campaign (olive campaigns run October -> September).
uv run python scripts/extract_monthly_indices.py --province 23 --municipality 60 \
    --start 2024-10-01 --end 2025-10-01
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from oliveye.pipeline.openeo_indices import (
    build_monthly_indices,
    clean_monthly_indices,
    load_indices_csv,
    olive_area_by_municipality,
    request_summary,
)
from oliveye.pipeline.openeo_jobs import cache_key, run_cached_batch_job
from oliveye.pipeline.sigpac import fetch_and_cache_municipality

REPO_ROOT = Path(__file__).resolve().parents[1]
SIGPAC_DIR = REPO_ROOT / "data" / "raw" / "sigpac"
CACHE_DIR = REPO_ROOT / "data" / "cache" / "openeo"
INTERIM_DIR = REPO_ROOT / "data" / "interim"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--province", required=True, help="INE province code, e.g. 23 (Jaén)")
    parser.add_argument("--municipality", required=True, help="municipality code, e.g. 60")
    parser.add_argument("--start", required=True, help="inclusive, first day of a month")
    parser.add_argument("--end", required=True, help="exclusive, first day of a month")
    parser.add_argument(
        "--dry-run", action="store_true", help="build and save the request, do not run it"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    sigpac_path = fetch_and_cache_municipality(args.province, args.municipality, SIGPAC_DIR)
    areas = olive_area_by_municipality(gpd.read_parquet(sigpac_path))
    print(json.dumps(request_summary(areas), indent=1))

    if args.dry_run:
        process = build_monthly_indices(areas, args.start, args.end)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        graph_path = CACHE_DIR / f"{cache_key(process)}.dryrun.process.json"
        graph_path.write_text(json.dumps(process.flat_graph(), indent=1))
        print(f"Dry run: process graph saved to {graph_path} (0 credits)")
        return

    from oliveye.pipeline.openeo_auth import connect_cdse  # imported here: --dry-run is offline

    connection = connect_cdse()
    process = build_monthly_indices(areas, args.start, args.end, connection=connection)
    title = f"oliveye monthly indices {args.province}/{args.municipality} {args.start}..{args.end}"
    csv_path = run_cached_batch_job(process, CACHE_DIR, title)

    tidy = clean_monthly_indices(load_indices_csv(csv_path, areas))
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / (
        f"indices_monthly_{args.province}_{args.municipality}_{args.start}_{args.end}.parquet"
    )
    tidy.assign(month=tidy["month"].astype(str)).to_parquet(out)

    with pd.option_context("display.width", 120):
        print(tidy[["month", "ndvi", "ndmi", "ndvi_outlier", "ndmi_outlier"]].round(3))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
