"""Offline tests for oliveye.pipeline.openeo_ndvi (no openEO connection, no credits spent)."""

import csv
import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from oliveye.pipeline.openeo_ndvi import (
    build_ndvi_timeseries,
    cache_key,
    load_ndvi_csv,
    prepare_geometries,
    run_cached_batch_job,
    select_parcels,
)

# A point inside Martos (Jaén) in EPSG:25830, so reprojections give realistic lon/lat.
X0, Y0 = 410_000.0, 4_170_000.0


@pytest.fixture
def parcels() -> gpd.GeoDataFrame:
    """Four 4-ha squares of olive, one 1-ha arable square, one thin olive strip."""
    geoms = [box(X0 + i * 500, Y0, X0 + i * 500 + 200, Y0 + 200) for i in range(4)]
    geoms.append(box(X0, Y0 + 500, X0 + 100, Y0 + 600))  # 1 ha arable
    geoms.append(box(X0, Y0 + 1000, X0 + 2000, Y0 + 1020))  # 4 ha, but 2 km x 20 m
    gdf = gpd.GeoDataFrame(
        {
            "parcel_id": ["ov1", "ov2", "ov3", "ov4", "ta1", "strip"],
            "land_use_code": ["OV", "OV", "OV", "OV", "TA", "OV"],
        },
        geometry=geoms,
        crs="EPSG:25830",
    )
    gdf["area_ha"] = gdf.area / 1e4
    return gdf


def test_select_is_reproducible_and_skips_thin_parcels(parcels: gpd.GeoDataFrame) -> None:
    first = select_parcels(parcels, "OV", 3, seed=1)
    second = select_parcels(parcels, "OV", 3, seed=1)

    assert list(first["parcel_id"]) == list(second["parcel_id"])
    assert "strip" not in set(first["parcel_id"])


def test_select_falls_back_to_largest_with_warning(parcels: gpd.GeoDataFrame) -> None:
    with pytest.warns(UserWarning, match="largest compact"):
        chosen = select_parcels(parcels, "TA", 1, min_area_ha=3.0)
    assert list(chosen["parcel_id"]) == ["ta1"]


def test_select_respects_distance(parcels: gpd.GeoDataFrame) -> None:
    anchor = parcels[parcels["parcel_id"] == "ov1"]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        chosen = select_parcels(parcels, "OV", 2, near=anchor, max_distance_m=400)
    assert set(chosen["parcel_id"]) == {"ov1", "ov2"}  # ov3/ov4 are > 400 m away


def test_prepare_geometries_shrinks_and_reprojects(parcels: gpd.GeoDataFrame) -> None:
    prepared = prepare_geometries(parcels.iloc[:4], inner_buffer_m=10)

    assert prepared.crs.to_epsg() == 4326
    assert prepared.to_crs(25830).area.iloc[0] == pytest.approx(180 * 180)
    assert list(prepared.index) == [0, 1, 2, 3]


def test_process_graph_masks_clouds_and_aggregates(parcels: gpd.GeoDataFrame) -> None:
    geoms = prepare_geometries(parcels.iloc[:2])
    graph = build_ndvi_timeseries(geoms, "2024-01-01", "2026-01-01").flat_graph()

    processes = {node["process_id"] for node in graph.values()}
    assert {"load_collection", "mask", "ndvi", "aggregate_spatial"} <= processes
    load = graph["loadcollection1"]["arguments"]
    assert load["bands"] == ["B04", "B08", "SCL"]
    assert load["temporal_extent"] == ["2024-01-01", "2026-01-01"]
    assert len(graph["aggregatespatial1"]["arguments"]["geometries"]["features"]) == 2


def test_cache_key_changes_with_dates(parcels: gpd.GeoDataFrame) -> None:
    geoms = prepare_geometries(parcels.iloc[:2])
    a = build_ndvi_timeseries(geoms, "2024-01-01", "2026-01-01")
    b = build_ndvi_timeseries(geoms, "2024-01-01", "2026-01-01")
    c = build_ndvi_timeseries(geoms, "2024-01-01", "2025-01-01")

    assert cache_key(a) == cache_key(b)
    assert cache_key(a) != cache_key(c)


class _FakeJob:
    """Minimal openEO BatchJob: 'created' until started, then 'finished'."""

    job_id = "j-123"

    def __init__(self, state: str = "created") -> None:
        self.state = state
        self.starts = 0

    def status(self) -> str:
        return self.state

    def start(self) -> None:
        self.starts += 1
        self.state = "finished"

    def get_results(self) -> "_FakeJob":
        return self

    def download_files(self, target: str) -> None:
        Path(target, "timeseries.csv").write_text(
            "date,feature_index,NDVI\n2024-05-01T00:00:00Z,0,0.42\n2024-05-01T00:00:00Z,1,\n"
        )

    def describe(self) -> dict[str, Any]:
        return {"costs": 12.5, "status": "finished"}


class _FakeConnection:
    def __init__(self, job: _FakeJob) -> None:
        self._job = job
        self.resumed: list[str] = []

    def job(self, job_id: str) -> _FakeJob:
        self.resumed.append(job_id)
        return self._job


class _FakeProcess:
    """Stands in for an openEO VectorCube; counts how many jobs are created."""

    def __init__(self) -> None:
        self.jobs_created = 0
        self.connection = _FakeConnection(_FakeJob("finished"))

    def flat_graph(self) -> dict[str, Any]:
        return {"node": {"process_id": "fake", "arguments": {}}}

    def create_job(self, title: str, out_format: str) -> _FakeJob:
        self.jobs_created += 1
        return _FakeJob()


def test_batch_job_runs_once_then_uses_cache(tmp_path: Path, parcels: gpd.GeoDataFrame) -> None:
    process = _FakeProcess()

    first = run_cached_batch_job(process, tmp_path, "test")
    second = run_cached_batch_job(process, tmp_path, "test")

    assert first == second
    assert process.jobs_created == 1
    with (tmp_path / "credits_log.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert [r["status"] for r in rows] == ["created", "finished"]  # one job, two log rows
    assert rows[1]["costs"] == "12.5"

    tidy = load_ndvi_csv(first, prepare_geometries(parcels.iloc[:2]))
    assert list(tidy.columns) == ["date", "parcel_id", "land_use_code", "ndvi"]
    assert len(tidy) == 1  # the fully masked observation is dropped
    assert tidy.loc[0, "parcel_id"] == "ov1"
    assert tidy.loc[0, "date"] == pd.Timestamp("2024-05-01")


def test_load_csv_with_input_bands_kept(tmp_path: Path, parcels: gpd.GeoDataFrame) -> None:
    """Real CDSE output keeps B04/B08 next to the NDVI band."""
    path = tmp_path / "cdse.csv"
    path.write_text(
        "date,feature_index,B04,B08,NDVI\n"
        "2024-05-01T00:00:00.000Z,0,0.05,0.30,0.71\n"
        "2024-05-01T00:00:00.000Z,1,,,\n"
    )
    tidy = load_ndvi_csv(path, prepare_geometries(parcels.iloc[:2]))

    assert len(tidy) == 1
    assert tidy.loc[0, "ndvi"] == pytest.approx(0.71)


class _FailingJob(_FakeJob):
    def start(self) -> None:
        raise RuntimeError("backend error")

    def describe(self) -> dict[str, Any]:
        return {"costs": 3.0, "status": "error"}


def test_failed_job_still_logs_its_credits(tmp_path: Path) -> None:
    process = _FakeProcess()
    process.create_job = lambda title, out_format: _FailingJob()  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="backend error"):
        run_cached_batch_job(process, tmp_path, "test")

    with (tmp_path / "credits_log.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert [(r["status"], r["costs"]) for r in rows] == [("created", ""), ("error", "3.0")]


def test_failed_job_is_not_retried_automatically(tmp_path: Path) -> None:
    process = _FakeProcess()
    process.create_job = lambda title, out_format: _FailingJob()  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        run_cached_batch_job(process, tmp_path, "test")

    with pytest.raises(RuntimeError, match="Inspect its logs before paying"):
        run_cached_batch_job(_FakeProcess(), tmp_path, "test")


class _StuckJob(_FakeJob):
    def start(self) -> None:
        self.state = "running"

    def describe(self) -> dict[str, Any]:
        return {"costs": "", "status": "running"}


def test_unfinished_job_is_resumed_not_paid_twice(tmp_path: Path) -> None:
    stuck = _FakeProcess()
    stuck.create_job = lambda title, out_format: _StuckJob()  # type: ignore[method-assign]
    with pytest.raises(TimeoutError):
        run_cached_batch_job(stuck, tmp_path, "test", timeout_s=0, poll_s=0)

    # Next run (e.g. the next push): the job finished meanwhile on the backend.
    later = _FakeProcess()
    path = run_cached_batch_job(later, tmp_path, "test")

    assert later.jobs_created == 0  # no second job
    assert later.connection.resumed == ["j-123"]
    assert later.connection._job.starts == 0  # a finished job is never restarted
    assert path.exists()
    with (tmp_path / "credits_log.csv").open() as fh:
        statuses = [r["status"] for r in csv.DictReader(fh)]
    assert statuses == ["created", "running", "resumed", "finished"]
