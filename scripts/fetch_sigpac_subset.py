"""CLI: explore and download SIGPAC subsets for one municipality.

Examples
--------
# 1. Which municipalities of Jaén (23) have the most olive groves?
uv run python scripts/fetch_sigpac_subset.py --province 23 --rank

# 2. Download olive (OV) and arable (TA) parcels of one of them into data/raw/sigpac/
uv run python scripts/fetch_sigpac_subset.py --province 23 --municipality 60
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd

from oliveye.pipeline.sigpac import (
    SIGPAC_ANDALUSIA_URL,
    fetch_and_cache_municipality,
    rank_municipalities_by_olive_area,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "raw" / "sigpac"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--province", required=True, help="INE province code, e.g. 23 (Jaén), 18 (Granada)"
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--rank", action="store_true", help="rank municipalities by olive area")
    action.add_argument("--municipality", help="municipality code as shown by --rank")
    parser.add_argument("--limit", type=int, default=15, help="rows shown by --rank")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--source", default=SIGPAC_ANDALUSIA_URL, help="GeoParquet URL or local path"
    )
    parser.add_argument("--force", action="store_true", help="re-download even if cached")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.rank:
        print(f"Ranking municipalities of province {args.province} by olive area (OV)...")
        ranking = rank_municipalities_by_olive_area(
            args.province, source=args.source, limit=args.limit
        )
        print(f"{'municipality':>12} {'parcels':>9} {'olive_ha':>10}")
        for row in ranking:
            print(f"{row.municipality_code:>12} {row.parcels:>9,} {row.olive_hectares:>10,.0f}")
        return

    path = fetch_and_cache_municipality(
        args.province, args.municipality, args.output_dir, source=args.source, force=args.force
    )
    parcels = gpd.read_parquet(path)
    print(f"Saved {len(parcels):,} parcels to {path}")
    print(parcels.groupby("land_use_code")["area_ha"].agg(["count", "sum"]).round(1))


if __name__ == "__main__":
    main()
