"""NDVI time series per parcel from Sentinel-2 via openEO, with local caching and credit logging.

Quota-friendly by design (see CLAUDE.md, "Copernicus free-quota rules"):

* only the bands B04 (red), B08 (near infrared) and SCL (scene classification) are loaded;
* clouds, shadows and snow are masked on the server using SCL;
* NDVI is computed and averaged per parcel on the server (`aggregate_spatial`), so only a small
  CSV (date x parcel) is downloaded, never images;
* one batch job per request; its result is cached under a hash of the process graph, so running
  the same request twice never spends credits twice;
* the credits reported by the backend for each job are appended to `credits_log.csv`.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import geopandas as gpd
import pandas as pd
from openeo.rest.datacube import DataCube

COLLECTION_ID = "SENTINEL2_L2A"
BANDS: list[str] = ["B04", "B08", "SCL"]

# Sentinel-2 L2A Scene Classification (SCL) classes we KEEP. Everything else (no data,
# saturated, cloud shadows, water, unclassified, clouds, cirrus, snow) is masked out.
SCL_VEGETATION = 4
SCL_NOT_VEGETATED = 5  # bare soil: frequent between olive trees, must be kept

METRIC_CRS = "EPSG:25830"  # ETRS89 / UTM 30N: metres, for areas and buffers
OPENEO_CRS = "EPSG:4326"  # lon/lat, what openEO expects for GeoJSON geometries

CREDITS_LOG_FIELDS = ["logged_at", "job_id", "title", "cache_key", "costs", "status"]


# --------------------------------------------------------------------------------------------
# 1. Parcel selection
# --------------------------------------------------------------------------------------------


def compactness(gdf: gpd.GeoDataFrame) -> pd.Series:
    """Polsby-Popper compactness: 4*pi*area / perimeter^2 (1 = circle, ~0.79 = square).

    Long, thin parcels are mostly border pixels, so we prefer compact ones.
    """
    ratio: pd.Series = 4 * math.pi * gdf.geometry.area / gdf.geometry.length**2
    return ratio


def select_parcels(
    parcels: gpd.GeoDataFrame,
    land_use_code: str,
    n: int,
    *,
    min_area_ha: float = 3.0,
    min_compactness: float = 0.5,
    near: gpd.GeoDataFrame | None = None,
    max_distance_m: float = 2_000.0,
    seed: int = 42,
) -> gpd.GeoDataFrame:
    """Pick `n` compact parcels of one land use, reproducibly.

    Args:
        parcels: SIGPAC parcels in a metric CRS (EPSG:25830).
        land_use_code: SIGPAC code, e.g. "OV" (olive grove) or "TA" (arable land).
        n: number of parcels to return.
        min_area_ha: preferred minimum area. If fewer than `n` parcels qualify, the `n` largest
            compact ones are returned instead and a warning is emitted.
        min_compactness: Polsby-Popper threshold.
        near: if given, only parcels within `max_distance_m` of these geometries are eligible.
            Keeping all samples close together keeps the openEO bounding box (and cost) small
            and makes weather conditions comparable between parcels.
        max_distance_m: radius used with `near`.
        seed: random seed, so the same parcels are selected every run.
    """
    if parcels.crs is None or parcels.crs.to_string() != METRIC_CRS:
        raise ValueError(f"Parcels must be in {METRIC_CRS} to measure areas in metres.")

    candidates = parcels[parcels["land_use_code"] == land_use_code]
    candidates = candidates[compactness(candidates) >= min_compactness]
    if near is not None:
        zone = near.to_crs(METRIC_CRS).buffer(max_distance_m).union_all()
        candidates = candidates[candidates.intersects(zone)]

    large = candidates[candidates["area_ha"] >= min_area_ha]
    if len(large) >= n:
        chosen = large.sample(n=n, random_state=seed)
    else:
        warnings.warn(
            f"Only {len(large)} '{land_use_code}' parcels >= {min_area_ha} ha; "
            f"using the {n} largest compact ones instead.",
            stacklevel=2,
        )
        chosen = candidates.nlargest(n, "area_ha")
    if len(chosen) < n:
        raise ValueError(f"Not enough '{land_use_code}' parcels: found {len(chosen)}, need {n}.")
    return chosen.copy()


def prepare_geometries(parcels: gpd.GeoDataFrame, inner_buffer_m: float = 10.0) -> gpd.GeoDataFrame:
    """Shrink parcels inwards and reproject them for openEO.

    A negative buffer of one Sentinel-2 pixel (10 m) drops border pixels that mix the crop with
    roads, field margins or neighbouring parcels ("mixed pixels").
    The row order of the returned frame is the `feature_index` used by openEO in the results.
    """
    shrunk = parcels.to_crs(METRIC_CRS).copy()
    shrunk["geometry"] = shrunk.buffer(-inner_buffer_m)
    shrunk = shrunk[~shrunk.geometry.is_empty]
    return shrunk.to_crs(OPENEO_CRS).reset_index(drop=True)


# --------------------------------------------------------------------------------------------
# 2. openEO process
# --------------------------------------------------------------------------------------------


def spatial_extent(geometries: gpd.GeoDataFrame, margin_deg: float = 0.002) -> dict[str, float]:
    """Tight lon/lat bounding box around the geometries (~200 m margin)."""
    west, south, east, north = geometries.to_crs(OPENEO_CRS).total_bounds
    return {
        "west": round(float(west) - margin_deg, 5),
        "south": round(float(south) - margin_deg, 5),
        "east": round(float(east) + margin_deg, 5),
        "north": round(float(north) + margin_deg, 5),
    }


def build_ndvi_timeseries(
    geometries: gpd.GeoDataFrame,
    start_date: str,
    end_date: str,
    *,
    connection: Any = None,
) -> Any:
    """Build (without executing) the openEO process: masked NDVI averaged per geometry.

    Args:
        geometries: parcels in EPSG:4326, already shrunk (see `prepare_geometries`).
        start_date: inclusive, "YYYY-MM-DD".
        end_date: exclusive, "YYYY-MM-DD".
        connection: authenticated `openeo.Connection`. With `None` the graph is built offline,
            which is handy for tests and for inspecting the request before paying for it.

    Returns:
        An openEO `VectorCube` (one NDVI value per date and geometry).
    """
    cube = DataCube.load_collection(
        COLLECTION_ID,
        connection=connection,
        spatial_extent=spatial_extent(geometries),
        temporal_extent=[start_date, end_date],
        bands=BANDS,
        fetch_metadata=connection is not None,
    )
    scl = cube.band("SCL")
    cloudy: DataCube = (scl != SCL_VEGETATION) & (scl != SCL_NOT_VEGETATED)  # True = discard pixel
    ndvi = (
        cube.filter_bands(["B04", "B08"])
        .mask(cloudy)
        .ndvi(nir="B08", red="B04", target_band="NDVI")
    )

    feature_collection = json.loads(geometries[["geometry"]].to_json())
    return ndvi.aggregate_spatial(geometries=feature_collection, reducer="mean")


# --------------------------------------------------------------------------------------------
# 3. Execution with cache and credit logging
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
    print(f"Started batch job {job.job_id}; this usually takes a few minutes...")
    job.start_and_wait()

    with tempfile.TemporaryDirectory(dir=cache_dir) as tmp:
        job.get_results().download_files(tmp)
        produced = sorted(Path(tmp).rglob("*.csv"))
        if not produced:
            raise RuntimeError(f"Job {job.job_id} finished but returned no CSV file.")
        shutil.move(produced[0], csv_path)

    metadata: dict[str, Any] = job.describe()
    log_credits(
        cache_dir / "credits_log.csv",
        {
            "logged_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "job_id": str(job.job_id),
            "title": title,
            "cache_key": key,
            "costs": str(metadata.get("costs", "")),
            "status": str(metadata.get("status", "")),
        },
    )
    print(f"Saved {csv_path.name}; credits charged: {metadata.get('costs', 'n/a')}")
    return csv_path


# --------------------------------------------------------------------------------------------
# 4. Reading results
# --------------------------------------------------------------------------------------------


def load_ndvi_csv(csv_path: Path, geometries: gpd.GeoDataFrame) -> pd.DataFrame:
    """Turn the openEO CSV into a tidy table: date, parcel_id, land_use_code, ndvi.

    openEO identifies parcels by `feature_index` (their row order in the request), so we join it
    back to the same `geometries` frame that was sent. Dates where every pixel was masked come
    back empty (NaN) and are dropped.

    The CDSE backend keeps the input bands next to the target band, so the CSV may contain
    `B04`, `B08` and `NDVI`; we pick the `NDVI` column when present.
    """
    raw = pd.read_csv(csv_path)
    value_columns = [c for c in raw.columns if c not in ("date", "feature_index")]
    if "NDVI" in value_columns:
        ndvi_column = "NDVI"
    elif len(value_columns) == 1:
        ndvi_column = value_columns[0]
    else:
        raise ValueError(f"Cannot find the NDVI column among {value_columns}")

    tidy = raw.rename(columns={ndvi_column: "ndvi"})
    tidy["date"] = pd.to_datetime(tidy["date"]).dt.tz_localize(None).dt.normalize()
    attributes = geometries.drop(columns="geometry").reset_index(drop=True)
    tidy = tidy.merge(attributes, left_on="feature_index", right_index=True, how="left")
    tidy = tidy.dropna(subset=["ndvi"])
    columns = ["date", "parcel_id", "land_use_code", "ndvi"]
    return tidy[columns].sort_values(["parcel_id", "date"]).reset_index(drop=True)
