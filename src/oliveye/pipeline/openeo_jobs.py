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
import time
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


# Job states after which nothing more will happen on the backend.
TERMINAL_STATES = ("finished", "error", "canceled")
DEFAULT_TIMEOUT_S = 150 * 60  # below the 180-minute GitHub Actions limit


def credits_log_path(cache_dir: Path, key: str) -> Path:
    """Credits log of one request (cache key)."""
    return cache_dir / "credits" / f"{key}.csv"


def credits_table(cache_dir: Path) -> list[dict[str, str]]:
    """Every logged row: the per-request logs plus the legacy single `credits_log.csv`."""
    paths = sorted((cache_dir / "credits").glob("*.csv"))
    legacy = cache_dir / "credits_log.csv"
    rows: list[dict[str, str]] = []
    for path in [legacy, *paths] if legacy.exists() else paths:
        with path.open(encoding="utf-8") as fh:
            rows.extend(csv.DictReader(fh))
    return sorted(rows, key=lambda row: row["logged_at"])


def unfinished_job_id(cache_dir: Path, key: str) -> str | None:
    """Job id of an earlier batch job for `key` whose last logged state is not terminal.

    Used to resume instead of paying for a second job when an earlier run died (runner killed,
    timeout, failed download) after the job was created. Reads every log (per-request files and
    the legacy single log), so no earlier job is missed.
    """
    rows = [row for row in credits_table(cache_dir) if row["cache_key"] == key]
    if not rows:
        return None
    last = rows[-1]
    if last["status"] in ("error", "canceled"):
        raise RuntimeError(
            f"The last openEO job for cache key {key} ({last['job_id']}) ended in "
            f"'{last['status']}'. Inspect its logs before paying for a retry."
        )
    return last["job_id"] or None


def backend_job_id(
    connection: Any,
    keyed_title: str,
    legacy_title: str,
    known_job_ids: set[str],
) -> str | None:
    """Newest usable batch job on the backend for this request, if one exists.

    Last line of defence against paying twice: if the local log was lost (e.g. a CI run died
    before publishing it), the job still exists on openEO under its title, so we reuse it.

    * `keyed_title` ("<title> [<cache key>]") identifies the exact request.
    * `legacy_title` (no key, used before keys were added) is accepted only for jobs that are
      not in our logs at all: a logged job belongs to a known request and must never be
      reused for a different one.
    * Jobs in 'error' or 'canceled' are ignored.

    Fails closed: if the listing fails, raise instead of risking a duplicate paid job.
    """
    try:
        listing = list(connection.list_jobs(limit=500))
    except Exception as error:
        raise RuntimeError(
            "Could not list openEO jobs to check for an existing one; not creating a new job."
        ) from error
    usable = [
        job
        for job in listing
        if job.get("status") not in ("error", "canceled")
        and (
            job.get("title") == keyed_title
            or (job.get("title") == legacy_title and str(job.get("id")) not in known_job_ids)
        )
    ]
    if not usable:
        return None
    return str(max(usable, key=lambda job: str(job.get("created", "")))["id"])


def _wait(job: Any, timeout_s: float, poll_s: float) -> str:
    """Poll until the job reaches a terminal state; raise TimeoutError after `timeout_s`."""
    deadline = time.monotonic() + timeout_s
    while True:
        status = str(job.status())
        if status in TERMINAL_STATES:
            return status
        if time.monotonic() > deadline:
            raise TimeoutError(f"Job {job.job_id} still '{status}' after {timeout_s:.0f} s")
        time.sleep(poll_s)


def run_cached_batch_job(
    process: Any,
    cache_dir: Path,
    title: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    poll_s: float = 30.0,
) -> Path:
    """Run `process` as one openEO batch job and return the CSV path, or reuse the cached CSV.

    Credit safety:

    * the cache check happens BEFORE contacting the backend (a hit costs 0 credits);
    * a row is logged as soon as the job exists, and a final row even if anything fails;
    * if an earlier job for the same request never finished (e.g. the runner was killed), it is
      **resumed** by id instead of creating and paying for a new one;
    * a finished job is never restarted: its results are only downloaded.
    """
    key = cache_key(process)
    csv_path = cache_dir / f"{key}.csv"
    if csv_path.exists():
        print(f"Cache hit: {csv_path.name} (0 credits)")
        return csv_path

    cache_dir.mkdir(parents=True, exist_ok=True)
    # One log file per request: parallel CI workers never edit the same file, so publishing their
    # results to git can always be rebased without conflicts.
    log_path = credits_log_path(cache_dir, key)
    graph_path = cache_dir / f"{key}.process.json"
    graph_path.write_text(json.dumps(process.flat_graph(), separators=(",", ":")))

    # The cache key in the title lets a lost job be found again on the backend; the plain title
    # matches jobs created before keys were added (same code, same request).
    keyed_title = f"{title} [{key}]"
    previous = unfinished_job_id(cache_dir, key)
    origin = "resumed"
    if not previous:
        known = {row["job_id"] for row in credits_table(cache_dir)}
        previous = backend_job_id(process.connection, keyed_title, title, known)
        origin = "recovered"
    if previous:
        job = process.connection.job(previous)
        print(f"{origin.capitalize()} batch job {previous} (cache key {key}): no new job created")
    else:
        job = process.create_job(title=keyed_title, out_format="CSV")
        origin = "created"

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
    log(origin)
    print(f"Batch job {job.job_id} (cache key {key}); this usually takes a few minutes...")
    metadata: dict[str, Any] = {}
    try:
        if str(job.status()) == "created":
            job.start()
        final = _wait(job, timeout_s, poll_s)
        if final != "finished":
            raise RuntimeError(f"Job {job.job_id} ended in '{final}'")
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
