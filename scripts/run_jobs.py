"""CLI: run every pending job in `jobs/` and write its results (used by GitHub Actions).

    uv run python scripts/run_jobs.py --results-dir ../results

Exit code is 1 if any job failed, so the workflow run shows up red, but all jobs still run and
every result (including failures) is published.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from oliveye.jobs import load_job, pending_jobs, run_job

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-dir", type=Path, default=REPO_ROOT / "jobs")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--sigpac-dir", type=Path, default=REPO_ROOT / "data" / "raw" / "sigpac")
    args = parser.parse_args()

    openeo_cache_dir = args.results_dir / "_cache" / "openeo"
    pending = pending_jobs(args.jobs_dir, args.results_dir)
    print(f"{len(pending)} pending job(s)")

    failed = 0
    for path in pending:
        try:
            job = load_job(path)
        except ValueError as error:
            # Record the failure so the same broken file is not retried on every push.
            print(f"Invalid job: {error}")
            out = args.results_dir / path.stem
            out.mkdir(parents=True, exist_ok=True)
            invalid = {"job_id": path.stem, "status": "invalid", "error": str(error)}
            (out / "status.json").write_text(json.dumps(invalid, indent=1), encoding="utf-8")
            failed += 1
            continue
        status = run_job(
            job, args.results_dir, openeo_cache_dir=openeo_cache_dir, sigpac_dir=args.sigpac_dir
        )
        print(f"-> {job.job_id}: {status['status']}")
        failed += status["status"] != "ok"
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
