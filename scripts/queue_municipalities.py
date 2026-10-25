"""CLI: write openEO job files for the municipalities that hold most of a province's olive grove.

Reads the SIGPAC ranking CSVs produced by `sigpac_rank` jobs (results branch) and writes one
`openeo_monthly_indices` job per municipality, largest first, until `--coverage` of the
province's olive area is reached. Jobs are dry runs unless `--real` is given; existing job files
are never overwritten.

    git show origin/results:2026-10-24-sigpac-rank-23/olive_ranking_23.csv > /tmp/rank_23.csv
    uv run python scripts/queue_municipalities.py --ranking /tmp/rank_23.csv --province 23 \
        --coverage 0.8 --start 2016-10-01 --end 2026-10-01 --tag 2016-2026

To extend the same municipalities to another period, take them from an earlier real run:

    uv run python scripts/queue_municipalities.py --like 2016-2026 --province 23 \
        --start 2015-10-01 --end 2016-10-01 --tag 2015-2016
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]


def select_municipalities(ranking: pd.DataFrame, coverage: float) -> list[str]:
    """Largest municipalities first, until their olive area reaches `coverage` of the total."""
    ordered = ranking.sort_values("olive_hectares", ascending=False)
    share = ordered["olive_hectares"].cumsum() / ordered["olive_hectares"].sum()
    n = int((share < coverage).sum()) + 1
    return [str(code) for code in ordered["municipality_code"].head(n)]


def municipalities_like(jobs_dir: Path, province: str, tag: str) -> list[str]:
    """Municipality codes of the real openEO jobs already queued with `tag` in `province`."""
    codes = []
    for path in sorted(jobs_dir.glob(f"*-openeo-real-{province}-*-{tag}.json")):
        params = json.loads(path.read_text(encoding="utf-8"))["params"]
        codes.append(str(params["municipality"]))
    return codes


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--ranking", type=Path, help="SIGPAC ranking CSV (sigpac_rank job)")
    source.add_argument("--like", help="reuse the municipalities of the real jobs with this tag")
    parser.add_argument("--province", required=True)
    parser.add_argument("--coverage", type=float, default=0.8)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--tag", required=True, help="suffix for job ids, e.g. 2016-2026")
    parser.add_argument("--real", action="store_true", help="spend credits (default: dry run)")
    parser.add_argument("--exclude", nargs="*", default=[], help="municipality codes to skip")
    parser.add_argument("--jobs-dir", type=Path, default=REPO_ROOT / "jobs")
    args = parser.parse_args()

    if args.like:
        codes = municipalities_like(args.jobs_dir, args.province, args.like)
    else:
        codes = select_municipalities(pd.read_csv(args.ranking), args.coverage)
    kind = "real" if args.real else "dryrun"
    written = 0
    for code in codes:
        if code in args.exclude:
            continue
        job_id = f"{date.today().isoformat()}-openeo-{kind}-{args.province}-{code}-{args.tag}"
        path = args.jobs_dir / f"{job_id}.json"
        if path.exists():
            continue
        spec = {
            "type": "openeo_monthly_indices",
            "params": {
                "province": args.province,
                "municipality": code,
                "start": args.start,
                "end": args.end,
                "dry_run": not args.real,
            },
        }
        path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        written += 1
    origin = f"like {args.like}" if args.like else f"cover {args.coverage:.0%}"
    print(f"{len(codes)} municipalities ({origin}); wrote {written} {kind} job(s)")


if __name__ == "__main__":
    main()
