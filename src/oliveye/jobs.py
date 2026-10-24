"""Unattended job runner: the work that needs internet, credentials or credits.

How it works (see `docs/automation.md`):

1. A job is a small JSON file in `jobs/`, e.g. `jobs/2026-10-24-sigpac-rank-jaen.json`:
   `{"type": "sigpac_rank", "params": {"province": "23"}}`. The file name (without `.json`)
   is the job id.
2. GitHub Actions runs `scripts/run_jobs.py` on every push that touches `jobs/`.
3. Each pending job runs once; its outputs, log and `status.json` are written to
   `<results>/<job id>/`, and the results are pushed to the `results` branch.

Only the job types registered in `HANDLERS` can run: a job file chooses a type and its
parameters, never a command. Jobs that spend openEO credits are dry runs unless they say
`"dry_run": false`, and their period is capped.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import traceback
import urllib.request
import zlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPMessage
from pathlib import Path
from typing import IO, Any, TextIO
from urllib.parse import urlparse

import geopandas as gpd
import pandas as pd

from oliveye.pipeline import sigpac

# Hosts the `download` job may fetch from: official statistics and data providers only.
ALLOWED_DOWNLOAD_HOSTS: tuple[str, ...] = (
    "juntadeandalucia.es",
    "mapa.gob.es",
    "aica.gob.es",
    "ine.es",
    "aemet.es",
    "source.coop",
)
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
# Measured on 2026-10-24 (Martos, 3,130 cells): 1 month = 4 credits, 12 months = 6 credits.
# The cost is mostly a fixed overhead per batch job, so the whole Sentinel-2 L2A history of one
# municipality (~10 years) fits in one job. The cap still stops a typo from requesting decades.
MAX_OPENEO_MONTHS = 120

ISO = "%Y-%m-%dT%H:%M:%SZ"

JOB_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
CODE_PATTERN = re.compile(r"\d{1,3}")  # INE province / Catastro municipality codes
SECRET_ENV_VARS = ("OPENEO_REFRESH_TOKEN", "OPENEO_CLIENT_SECRET")  # noqa: S105 - names only


@dataclass(frozen=True)
class JobContext:
    """Where a job reads and writes."""

    output_dir: Path  # <results>/<job id>/: everything here is published to the results branch
    openeo_cache_dir: Path  # persistent openEO cache + credits log (also on the results branch)
    sigpac_dir: Path  # local SIGPAC subsets (cached between CI runs, never committed)


Handler = Callable[[dict[str, Any], JobContext], list[Path]]


# --------------------------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------------------------


def _require(params: dict[str, Any], *names: str) -> None:
    missing = [name for name in names if name not in params]
    if missing:
        raise ValueError(f"Missing job parameters: {missing}")
    for name in ("province", "municipality"):
        if name in names and not CODE_PATTERN.fullmatch(str(params[name])):
            raise ValueError(f"'{name}' must be 1-3 digits, got {params[name]!r}")


def sigpac_rank(params: dict[str, Any], ctx: JobContext) -> list[Path]:
    """Olive-grove hectares per municipality of a province (no geometries downloaded)."""
    _require(params, "province")
    ranking = sigpac.rank_municipalities_by_olive_area(
        str(params["province"]), limit=int(params.get("limit", 1000))
    )
    table = pd.DataFrame([vars(row) for row in ranking])
    out = ctx.output_dir / f"olive_ranking_{params['province']}.csv"
    table.to_csv(out, index=False)
    print(table.head(20).to_string(index=False))
    print(f"{len(table)} municipalities, {table['olive_hectares'].sum():,.0f} ha of olive grove")
    return [out]


def sigpac_municipality_summary(params: dict[str, Any], ctx: JobContext) -> list[Path]:
    """Land-use counts, areas and lon/lat bounds of one municipality (e.g. to locate code 900)."""
    _require(params, "province", "municipality")
    path = sigpac.fetch_and_cache_municipality(
        str(params["province"]), str(params["municipality"]), ctx.sigpac_dir
    )
    parcels = gpd.read_parquet(path)
    summary = (
        parcels.groupby(["land_use_code", "land_use_name"])["area_ha"]
        .agg(parcels="count", hectares="sum")
        .reset_index()
        .sort_values("hectares", ascending=False)
    )
    west, south, east, north = parcels.to_crs("EPSG:4326").total_bounds
    bounds = {"west": west, "south": south, "east": east, "north": north}
    out_csv = ctx.output_dir / "land_use_summary.csv"
    out_json = ctx.output_dir / "bounds_epsg4326.json"
    summary.to_csv(out_csv, index=False)
    out_json.write_text(json.dumps({k: round(float(v), 5) for k, v in bounds.items()}, indent=1))
    print(summary.head(15).to_string(index=False))
    print(f"Bounds (EPSG:4326): {bounds}")
    return [out_csv, out_json]


def sigpac_schema(params: dict[str, Any], ctx: JobContext) -> list[Path]:
    """Columns of the remote SIGPAC file, plus the distinct admin values of one province.

    Used to find out whether the file carries municipality names or INE codes (it uses
    Catastro municipality codes, e.g. 900 = provincial capital).
    """
    _require(params, "province")
    con = sigpac._connect()
    source = sigpac.SIGPAC_ANDALUSIA_URL
    schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{source}')").df()
    schema_path = ctx.output_dir / "schema.csv"
    schema.to_csv(schema_path, index=False)
    print(schema[["column_name", "column_type"]].to_string(index=False))

    admin = [c for c in schema["column_name"] if str(c).startswith("admin")]
    columns = ", ".join(f'"{c}"' for c in admin)
    province_filter = sigpac._code_filter(con, source, "admin_province_code")
    values = con.execute(
        f"SELECT DISTINCT {columns} FROM read_parquet('{source}') WHERE {province_filter} "
        f"ORDER BY ALL",
        [str(params["province"])],
    ).df()
    values_path = ctx.output_dir / f"admin_values_{params['province']}.csv"
    values.to_csv(values_path, index=False)
    print(values.head(20).to_string(index=False))
    return [schema_path, values_path]


def _host_allowed(url: str) -> bool:
    """HTTPS only, and the host must be (a subdomain of) an allow-listed one."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return parsed.scheme == "https" and any(
        host == h or host.endswith("." + h) for h in ALLOWED_DOWNLOAD_HOSTS
    )


class _AllowListRedirects(urllib.request.HTTPRedirectHandler):
    """Re-check every redirect hop, so a redirect cannot leave the allow-list."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        if not _host_allowed(newurl):
            raise ValueError(f"Redirect to a host that is not allowed: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_AllowListRedirects)


def download(params: dict[str, Any], ctx: JobContext) -> list[Path]:
    """Download public files (e.g. the yearly aforo PDFs) from allow-listed official hosts.

    `params["files"]` maps an output file name to its URL.
    """
    _require(params, "files")
    files: dict[str, str] = params["files"]
    target = ctx.output_dir / "files"
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, url in files.items():
        if not _host_allowed(url):
            raise ValueError(f"Host not allowed for download: {url}")
        safe_name = Path(name).name  # no directories: a job cannot write outside its folder
        request = urllib.request.Request(url, headers={"User-Agent": "oliveye-jobs/0.1"})
        with _OPENER.open(request, timeout=120) as response:  # noqa: S310 - allow-listed
            content = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(content) > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"{url} is larger than {MAX_DOWNLOAD_BYTES} bytes")
        out = target / safe_name
        out.write_bytes(content)
        print(f"Downloaded {url} -> {out.name} ({len(content):,} bytes)")
        written.append(out)
    return written


def months_between(start: str, end: str) -> int:
    """Number of whole months in [start, end); both must be the first day of a month."""
    for value in (start, end):
        if pd.Timestamp(value).day != 1:
            raise ValueError(f"Dates must be the first day of a month, got {value!r}")
    return (pd.Period(end, "M") - pd.Period(start, "M")).n


def openeo_monthly_indices(params: dict[str, Any], ctx: JobContext) -> list[Path]:
    """Monthly NDVI/NDMI of one municipality's olive-dominant grid cells.

    Dry run unless `dry_run` is false. Optional params: `cell_m` (default 250) and
    `min_olive_share` (default 0.8). Outputs one series per cell and the olive-area-weighted
    series of the municipality.
    """
    from oliveye.pipeline import olive_grid as og
    from oliveye.pipeline import openeo_indices as oi
    from oliveye.pipeline.openeo_jobs import cache_key, run_cached_batch_job

    _require(params, "province", "municipality", "start", "end")
    province, municipality = str(params["province"]), str(params["municipality"])
    start, end = str(params["start"]), str(params["end"])
    n_months = months_between(start, end)
    if not 0 < n_months <= MAX_OPENEO_MONTHS:
        raise ValueError(f"Period must be 1..{MAX_OPENEO_MONTHS} months, got {n_months}")

    path = sigpac.fetch_and_cache_municipality(province, municipality, ctx.sigpac_dir)
    parcels = gpd.read_parquet(path)
    cells = og.olive_grid_cells(
        parcels,
        cell_m=int(params.get("cell_m", og.DEFAULT_CELL_M)),
        min_olive_share=float(params.get("min_olive_share", og.DEFAULT_MIN_OLIVE_SHARE)),
    )
    cells = cells[cells["municipality_code"].astype(str) == municipality].reset_index(drop=True)
    if cells.empty:
        raise ValueError(
            f"No olive-dominant cells in {province}/{municipality}; lower `min_olive_share`."
        )
    summary: dict[str, Any] = {
        **og.grid_summary(cells, parcels),
        "payload_bytes": oi.payload_bytes(cells),
        "months": n_months,
    }
    print(json.dumps(summary, indent=1))
    summary_path = ctx.output_dir / "request_summary.json"
    cells_path = ctx.output_dir / "cells.geojson"
    cells.to_crs("EPSG:4326").to_file(cells_path, driver="GeoJSON")

    # Only an explicit JSON `false` spends credits: null, 0, "" or a missing key are dry runs.
    if params.get("dry_run", True) is not False:
        process = oi.build_monthly_indices(cells, start, end)
        summary["cache_key"] = cache_key(process)
        summary_path.write_text(json.dumps(summary, indent=1))
        print("Dry run: nothing sent to openEO (0 credits).")
        return [summary_path, cells_path]

    from oliveye.pipeline.openeo_auth import auth_method, connect_cdse

    print(f"Authenticating with openEO ({auth_method()})...")
    connection = connect_cdse()
    process = oi.build_monthly_indices(cells, start, end, connection=connection)
    summary["cache_key"] = cache_key(process)
    summary_path.write_text(json.dumps(summary, indent=1))
    title = f"oliveye monthly indices {province}/{municipality} {start}..{end}"
    csv_path = run_cached_batch_job(process, ctx.openeo_cache_dir, title)

    per_cell = oi.load_indices_csv(csv_path, cells, id_columns=["cell_id"])
    stem = f"{province}_{municipality}_{start}_{end}"
    cells_out = ctx.output_dir / f"indices_cells_{stem}.csv"
    per_cell.assign(month=per_cell["month"].astype(str)).to_csv(cells_out, index=False)

    municipal = oi.clean_monthly_indices(og.aggregate_cells(per_cell, cells))
    out = ctx.output_dir / f"indices_monthly_{stem}.csv"
    municipal.assign(month=municipal["month"].astype(str)).to_csv(out, index=False)
    print(municipal[["month", "ndvi", "ndmi", "valid_cells", "ndvi_outlier"]].round(3).to_string())
    return [summary_path, cells_path, cells_out, out]


def aforo_table(params: dict[str, Any], ctx: JobContext) -> list[Path]:
    """Download Junta aforo PDFs and extract the provincial table into one CSV.

    `params["files"]` maps a file name containing the campaign (e.g. "aforo_2024_25.pdf") to
    its URL, exactly as in the `download` job.
    """
    from oliveye.pipeline.production import parse_aforo_pdfs

    pdfs = download(params, ctx)
    table = parse_aforo_pdfs(pdfs)
    out = ctx.output_dir / "aforo_by_province.csv"
    table.to_csv(out, index=False)
    focus = table[table["province"].isin(["Jaén", "Granada", "Andalucía"])]
    print(focus.to_string(index=False))
    return [*pdfs, out]


HANDLERS: dict[str, Handler] = {
    "aforo_table": aforo_table,
    "sigpac_rank": sigpac_rank,
    "sigpac_municipality_summary": sigpac_municipality_summary,
    "sigpac_schema": sigpac_schema,
    "download": download,
    "openeo_monthly_indices": openeo_monthly_indices,
}


# --------------------------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Job:
    job_id: str
    type: str
    params: dict[str, Any]


def load_job(path: Path) -> Job:
    """Parse and validate a job file. The job id is the file name without `.json`."""
    spec = json.loads(path.read_text(encoding="utf-8"))
    job_type = spec.get("type")
    if job_type not in HANDLERS:
        raise ValueError(f"{path.name}: unknown job type {job_type!r}; allowed: {list(HANDLERS)}")
    params = spec.get("params", {})
    if not isinstance(params, dict):
        raise ValueError(f"{path.name}: 'params' must be an object")
    if not is_valid_job_id(path.stem):
        raise ValueError(f"{path.name}: job ids may only contain letters, digits, '.', '_', '-'")
    return Job(job_id=path.stem, type=job_type, params=params)


class _Tee:
    """Write to several text streams at once (console + log file)."""

    def __init__(self, *streams: TextIO) -> None:
        self.streams = streams
        # log.txt is published as-is, outside GitHub's secret masking: redact secrets ourselves.
        self.secrets = [v for name in SECRET_ENV_VARS if len(v := os.environ.get(name, "")) >= 8]

    def write(self, text: str) -> int:
        for secret in self.secrets:
            text = text.replace(secret, "***")
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


@contextlib.contextmanager
def _capture_output(log_path: Path) -> Iterator[None]:
    with log_path.open("w", encoding="utf-8") as log:
        tee = _Tee(sys.stdout, log)
        with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
            yield


def run_job(
    job: Job, results_dir: Path, *, openeo_cache_dir: Path, sigpac_dir: Path
) -> dict[str, Any]:
    """Run one job, always leaving a `status.json` behind (also when it fails)."""
    output_dir = results_dir / job.job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    ctx = JobContext(output_dir, openeo_cache_dir, sigpac_dir)
    status: dict[str, Any] = {
        "job_id": job.job_id,
        "type": job.type,
        "params": job.params,
        "started_at": datetime.now(UTC).strftime(ISO),
    }
    with _capture_output(output_dir / "log.txt"):
        print(f"== {job.job_id} ({job.type})")
        try:
            outputs = HANDLERS[job.type](job.params, ctx)
            status.update(
                status="ok", outputs=[p.relative_to(output_dir).as_posix() for p in outputs]
            )
        except Exception as error:  # noqa: BLE001 - a failed job must not stop the others
            traceback.print_exc()
            status.update(status="error", error=f"{type(error).__name__}: {error}")
    status["finished_at"] = datetime.now(UTC).strftime(ISO)
    (output_dir / "status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    return status


def is_valid_job_id(job_id: str) -> bool:
    return bool(JOB_ID_PATTERN.fullmatch(job_id)) and ".." not in job_id


def result_dir_for(results_dir: Path, job_id: str) -> Path:
    """Results folder of a job; ids that could escape `results_dir` get a sanitised name."""
    if is_valid_job_id(job_id):
        return results_dir / job_id
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in job_id)
    return results_dir / f"invalid-{safe}"


def worker_of(path: Path, workers: int) -> int:
    """Worker that owns a job file when the queue is split between parallel workers.

    The split hashes the *request* (type + parameters without `dry_run`), not the file name, so
    two job files asking for the same openEO request always land on the same worker and run one
    after the other: the second one is then a free cache hit instead of a second paid job.
    Unreadable files go to worker 0, which records them as invalid.
    """
    if workers < 1:
        raise ValueError("workers must be >= 1")
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
        params = {k: v for k, v in dict(spec.get("params", {})).items() if k != "dry_run"}
        request = json.dumps({"type": spec.get("type"), "params": params}, sort_keys=True)
    except Exception:  # noqa: BLE001 - any broken file is handled by worker 0
        return 0
    return zlib.crc32(request.encode()) % workers


def pending_jobs(jobs_dir: Path, results_dir: Path) -> list[Path]:
    """Job files without a `status.json` in the results yet, oldest name first."""
    return [
        path
        for path in sorted(jobs_dir.glob("*.json"))
        if not (result_dir_for(results_dir, path.stem) / "status.json").exists()
    ]
