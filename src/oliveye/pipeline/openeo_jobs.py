"""Run openEO batch jobs with a local cache and a credits log (shared by every extraction).

Quota rules implemented here (see CLAUDE.md, "Copernicus free-quota rules"):

* one batch job per request, never many synchronous calls;
* the result is cached under a hash of the process graph, and the cache is checked BEFORE
  contacting the backend, so running the same request twice never spends credits twice;
* the credits reported by the backend for each job are appended to `credits_log.csv`.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

CREDITS_LOG_FIELDS = ["logged_at", "job_id", "title", "cache_key", "costs", "status"]


# --------------------------------------------------------------------------------------------


class _HasFlatGraph(Protocol):
    def flat_graph(self) -> dict[str, Any]: ...


def cache_key(process: _HasFlatGraph) -> str:
    """Deterministic key: same collection, dates, bands, geometries and steps -> same key."""
    canonical = json.dumps(process.flat_graph(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def log_credits(log_path: Path, row: dict[str, str]) -> None:
    """Append one row to the credits log, creating it with a header if needed."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CREDITS_LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def run_cached_batch_job(process: Any, cache_dir: Path, title: str) -> Path:
    """Run `process` as one openEO batch job and return the CSV path, or reuse the cached CSV.

    The cache check happens BEFORE contacting the backend, so a cache hit costs 0 credits.
    """
    key = cache_key(process)
    csv_path = cache_dir / f"{key}.csv"
    if csv_path.exists():
        print(f"Cache hit: {csv_path.name} (0 credits)")
        return csv_path

    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.process.json").write_text(json.dumps(process.flat_graph(), indent=1))

    job = process.create_job(title=title, out_format="CSV")
    log_path = cache_dir / "credits_log.csv"

    def log(status: str, costs: str = "") -> None:
        log_credits(
            log_path,
            {
                "logged_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "job_id": str(job.job_id),
                "title": title,
                "cache_key": key,
                "costs": costs,
                "status": status,
            },
        )

    # Logged before starting: if anything below fails, the job (and its credits) stays traceable.
    log("created")
    print(f"Started batch job {job.job_id} (cache key {key}); this usually takes a few minutes...")
    metadata: dict[str, Any] = {}
    try:
        job.start_and_wait()
        with tempfile.TemporaryDirectory(dir=cache_dir) as tmp:
            job.get_results().download_files(tmp)
            produced = sorted(Path(tmp).rglob("*.csv"))
            if not produced:
                raise RuntimeError(f"Job {job.job_id} finished but returned no CSV file.")
            shutil.move(produced[0], csv_path)
    finally:
        try:
            metadata = job.describe()
        except Exception:  # noqa: BLE001 - never hide the original error behind a logging one
            metadata = {}
        log(str(metadata.get("status", "unknown")), str(metadata.get("costs", "")))

    print(f"Saved {csv_path.name}; credits charged: {metadata.get('costs', 'n/a')}")
    return csv_path
