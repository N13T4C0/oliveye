"""Offline tests for the job runner (no network, no openEO credits)."""

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from oliveye import jobs
from oliveye.jobs import Job, JobContext, load_job, months_between, pending_jobs, run_job
from oliveye.pipeline.openeo_auth import auth_method, connect_cdse

X0, Y0 = 410_000.0, 4_170_000.0  # Martos (Jaén), EPSG:25830


@pytest.fixture
def ctx(tmp_path: Path) -> JobContext:
    out = tmp_path / "results" / "job"
    out.mkdir(parents=True)
    return JobContext(out, tmp_path / "cache", tmp_path / "sigpac")


@pytest.fixture
def fake_sigpac(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Replace the remote SIGPAC download with a small local GeoParquet file."""
    gdf = gpd.GeoDataFrame(
        {
            "parcel_id": ["a", "b"],
            "land_use_code": ["OV", "TA"],
            "land_use_name": ["OLIVAR", "TIERRAS ARABLES"],
            "province_code": ["23", "23"],
            "municipality_code": ["60", "60"],
        },
        geometry=[box(X0, Y0, X0 + 200, Y0 + 200), box(X0, Y0 + 500, X0 + 100, Y0 + 600)],
        crs="EPSG:25830",
    )
    gdf["area_ha"] = gdf.area / 1e4
    path = tmp_path / "sigpac.parquet"
    gdf.to_parquet(path)
    monkeypatch.setattr(jobs.sigpac, "fetch_and_cache_municipality", lambda *a, **k: path)
    return path


def write_job(directory: Path, name: str, spec: dict[str, object]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_text(json.dumps(spec))
    return path


def test_load_job_rejects_unknown_types(tmp_path: Path) -> None:
    path = write_job(tmp_path, "bad", {"type": "shell", "params": {"cmd": "rm -rf /"}})
    with pytest.raises(ValueError, match="unknown job type"):
        load_job(path)


def test_load_job_uses_file_name_as_id(tmp_path: Path) -> None:
    path = write_job(tmp_path, "2026-10-24-rank", {"type": "sigpac_rank", "params": {}})
    assert load_job(path) == Job("2026-10-24-rank", "sigpac_rank", {})


def test_download_only_from_allowed_hosts(ctx: JobContext) -> None:
    with pytest.raises(ValueError, match="Host not allowed"):
        jobs.download({"files": {"x.pdf": "https://example.com/x.pdf"}}, ctx)
    assert jobs._host_allowed("https://cdn.juntadeandalucia.es/a.pdf")
    assert not jobs._host_allowed("https://juntadeandalucia.es.evil.com/a.pdf")


def test_months_between() -> None:
    assert months_between("2024-10-01", "2025-10-01") == 12
    assert months_between("2025-07-01", "2025-08-01") == 1


def test_openeo_job_is_a_dry_run_by_default(ctx: JobContext, fake_sigpac: Path) -> None:
    params = {"province": "23", "municipality": "60", "start": "2025-07-01", "end": "2025-08-01"}
    outputs = jobs.openeo_monthly_indices(params, ctx)

    summary = json.loads(outputs[0].read_text())
    assert summary["olive_parcels"] == 1 and summary["months"] == 1
    assert len(summary["cache_key"]) == 16
    assert not ctx.openeo_cache_dir.exists()  # nothing was sent or cached


def test_openeo_job_caps_the_period(ctx: JobContext, fake_sigpac: Path) -> None:
    params = {"province": "23", "municipality": "60", "start": "2015-01-01", "end": "2026-01-01"}
    with pytest.raises(ValueError, match="Period must be"):
        jobs.openeo_monthly_indices(params, ctx)


def test_run_job_records_success_and_failure(tmp_path: Path, fake_sigpac: Path) -> None:
    results = tmp_path / "results"
    ok = run_job(
        Job("summary", "sigpac_municipality_summary", {"province": "23", "municipality": "60"}),
        results,
        openeo_cache_dir=tmp_path / "cache",
        sigpac_dir=tmp_path / "sigpac",
    )
    failed = run_job(
        Job("broken", "sigpac_municipality_summary", {}),
        results,
        openeo_cache_dir=tmp_path / "cache",
        sigpac_dir=tmp_path / "sigpac",
    )

    assert ok["status"] == "ok"
    assert ok["outputs"] == ["land_use_summary.csv", "bounds_epsg4326.json"]
    assert failed["status"] == "error" and "Missing job parameters" in failed["error"]
    assert "Traceback" in (results / "broken" / "log.txt").read_text()
    assert json.loads((results / "summary" / "status.json").read_text())["status"] == "ok"


def test_pending_jobs_skips_finished_ones(tmp_path: Path) -> None:
    jobs_dir, results = tmp_path / "jobs", tmp_path / "results"
    write_job(jobs_dir, "a", {"type": "sigpac_rank"})
    write_job(jobs_dir, "b", {"type": "sigpac_rank"})
    (results / "a").mkdir(parents=True)
    (results / "a" / "status.json").write_text("{}")

    assert [p.stem for p in pending_jobs(jobs_dir, results)] == ["b"]


def test_auth_method_priority() -> None:
    assert auth_method({}) == "interactive"
    assert auth_method({"OPENEO_REFRESH_TOKEN": "t"}) == "refresh_token"
    both = {"OPENEO_REFRESH_TOKEN": "t", "OPENEO_CLIENT_ID": "i", "OPENEO_CLIENT_SECRET": "s"}
    assert auth_method(both) == "client_credentials"


def test_ci_without_credentials_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Offline:
        def authenticate_oidc(self) -> None:
            raise AssertionError("must not start an interactive login in CI")

    monkeypatch.setattr("oliveye.pipeline.openeo_auth.connect", lambda url: _Offline())
    with pytest.raises(RuntimeError, match="No openEO credentials in CI"):
        connect_cdse({"CI": "true"})
