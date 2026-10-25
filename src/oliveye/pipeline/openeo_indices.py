"""Monthly NDVI and NDMI per municipality olive area from Sentinel-2 via openEO.

This is the Phase 2 extraction. Compared with `openeo_ndvi` (one value per parcel and per image)
it is built to scale to whole municipalities and provinces without burning the free quota:

* the unit is the **olive area of a municipality**: every SIGPAC olive parcel of the municipality
  dissolved into one (multi)polygon, so the output size does not grow with the number of parcels;
* bands B04 (red), B08 (near infrared), B11 (short-wave infrared) and SCL are loaded, nothing else;
* clouds, shadows and snow are masked on the server with SCL;
* NDVI and NDMI are computed per pixel, reduced to a **monthly median composite** on the server
  (the median discards most residual clouds that slip through the SCL mask), and only then
  averaged over each geometry. The download is a tiny CSV: month x municipality x index.

Indices (both range from -1 to 1):

* NDVI = (B08 - B04) / (B08 + B04): vegetation vigour / green biomass.
* NDMI = (B08 - B11) / (B08 + B11): canopy water content. B11 is absorbed by liquid water, so
  NDMI drops when the trees are water-stressed even if they still look green (NDVI stable).

Execution, caching and credit logging are delegated to `oliveye.pipeline.openeo_jobs`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from openeo.processes import ProcessBuilder, array_create
from openeo.rest.datacube import DataCube

from oliveye.pipeline.openeo_ndvi import (
    METRIC_CRS,
    OPENEO_CRS,
    SCL_NOT_VEGETATED,
    SCL_VEGETATION,
    spatial_extent,
)
from oliveye.pipeline.sigpac import OLIVE_GROVE

COLLECTION_ID = "SENTINEL2_L2A"
REFLECTANCE_BANDS: list[str] = ["B04", "B08", "B11"]
BANDS: list[str] = [*REFLECTANCE_BANDS, "SCL"]
INDEX_NAMES: list[str] = ["NDVI", "NDMI"]

# Columns that identify one geometry in the tidy output table.
AREA_ID_COLUMNS: list[str] = ["province_code", "municipality_code"]


# --------------------------------------------------------------------------------------------
# 1. Area of interest: olive area per municipality
# --------------------------------------------------------------------------------------------


def olive_area_by_municipality(
    parcels: gpd.GeoDataFrame,
    *,
    land_use_code: str = OLIVE_GROVE,
    inner_buffer_m: float = 10.0,
    simplify_tolerance_m: float = 5.0,
    min_part_ha: float = 0.0,
) -> gpd.GeoDataFrame:
    """Dissolve the olive parcels of each municipality into a single geometry for openEO.

    Steps, all in EPSG:25830 (metres):

    1. keep one land use (olive grove by default);
    2. shrink each parcel by one Sentinel-2 pixel (10 m) to drop mixed border pixels;
    3. dissolve per municipality, optionally drop polygon parts smaller than `min_part_ha`
       (tiny fragments add many vertices but almost no pixels), and simplify the outline
       (5 m is half a pixel, so the set of pixels covered barely changes).

    Returns:
        One row per municipality in EPSG:4326 with `n_parcels`, `olive_ha` (declared SIGPAC
        surface) and `sampled_ha` (surface actually measured after the inner buffer).
        The row order is the `feature_index` openEO uses in its results.
    """
    if parcels.crs is None or parcels.crs.to_string() != METRIC_CRS:
        raise ValueError(f"Parcels must be in {METRIC_CRS} to buffer in metres.")

    olive = parcels[parcels["land_use_code"] == land_use_code].copy()
    if olive.empty:
        raise ValueError(f"No parcels with land use '{land_use_code}'.")

    olive["geometry"] = olive.buffer(-inner_buffer_m)
    olive = olive[~olive.geometry.is_empty]

    stats = olive.groupby(AREA_ID_COLUMNS).agg(
        n_parcels=("parcel_id", "count"), olive_ha=("area_ha", "sum")
    )
    dissolved = olive[[*AREA_ID_COLUMNS, "geometry"]].dissolve(by=AREA_ID_COLUMNS)
    if min_part_ha > 0:
        parts = dissolved.explode(index_parts=False)
        parts = parts[parts.area >= min_part_ha * 1e4]
        dissolved = parts.dissolve(by=AREA_ID_COLUMNS)
    dissolved["geometry"] = dissolved.simplify(simplify_tolerance_m, preserve_topology=True)
    dissolved["sampled_ha"] = dissolved.area / 1e4

    areas = dissolved.join(stats).reset_index()
    columns = [*AREA_ID_COLUMNS, "n_parcels", "olive_ha", "sampled_ha", "geometry"]
    return areas[columns].to_crs(OPENEO_CRS)


# openEO on CDSE rejects requests of ~3 MB with "413 Request Entity Too Large" (seen on
# 2026-10-24 with Martos). Keep the inline GeoJSON well below that.
MAX_GEOMETRY_BYTES = 1_000_000

# (simplify tolerance in m, minimum polygon part in ha), from most to least detailed.
SIMPLIFICATION_STEPS: tuple[tuple[float, float], ...] = (
    (5, 0.0),
    (10, 0.0),
    (20, 0.1),
    (30, 0.25),
    (50, 0.5),
    (80, 1.0),
)


def geometry_payload(geometries: gpd.GeoDataFrame) -> dict[str, Any]:
    """The GeoJSON FeatureCollection sent inline to openEO (EPSG:4326, rounded coordinates).

    6 decimals of a degree is ~0.1 m: far below a 10 m pixel, and much shorter than full floats.
    """
    collection = json.loads(geometries.to_crs(OPENEO_CRS)[["geometry"]].to_json(drop_id=True))
    rounded: dict[str, Any] = _round_coordinates(collection, ndigits=6)
    return rounded


def payload_bytes(geometries: gpd.GeoDataFrame) -> int:
    """Size in bytes of `geometry_payload` as compact JSON."""
    return len(json.dumps(geometry_payload(geometries), separators=(",", ":")))


def olive_area_within_budget(
    parcels: gpd.GeoDataFrame,
    *,
    max_bytes: int = MAX_GEOMETRY_BYTES,
    max_area_loss: float = 0.25,
    steps: tuple[tuple[float, float], ...] = SIMPLIFICATION_STEPS,
) -> tuple[gpd.GeoDataFrame, dict[str, float]]:
    """Olive area per municipality, simplified just enough to fit the openEO request limit.

    Tries the steps in order and returns the first (most detailed) one that fits, with the
    settings used and the share of measured area lost, so it can be reported with the results.
    A step that loses more than `max_area_loss` of the measured area (or a municipality) is
    never accepted: a smaller request that no longer represents the olive grove is useless.
    """
    reference: gpd.GeoDataFrame | None = None
    for tolerance_m, min_part_ha in steps:
        areas = olive_area_by_municipality(
            parcels, simplify_tolerance_m=tolerance_m, min_part_ha=min_part_ha
        )
        if reference is None:
            reference = areas
        loss = 1 - areas["sampled_ha"].sum() / reference["sampled_ha"].sum()
        if len(areas) < len(reference) or loss > max_area_loss:
            break
        size = payload_bytes(areas)
        if size <= max_bytes:
            return areas, {
                "simplify_tolerance_m": tolerance_m,
                "min_part_ha": min_part_ha,
                "payload_bytes": size,
                "area_loss_pct": round(100 * float(loss), 2),
            }
    raise ValueError(
        f"Geometry does not fit in {max_bytes:,} bytes without losing more than "
        f"{max_area_loss:.0%} of the olive area; split the area into smaller requests."
    )


def _round_coordinates(obj: Any, ndigits: int) -> Any:
    """Recursively round every float in a GeoJSON-like structure."""
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, list):
        return [_round_coordinates(item, ndigits) for item in obj]
    if isinstance(obj, dict):
        return {k: _round_coordinates(v, ndigits) for k, v in obj.items()}
    return obj


def request_summary(areas: gpd.GeoDataFrame) -> dict[str, float | int]:
    """Size of an openEO request built from `areas`: it drives both cost and request limits.

    Computed in EPSG:25830 so that areas are in km², whatever the CRS of `areas`.
    """
    metric = areas.to_crs(METRIC_CRS)
    west, south, east, north = metric.total_bounds
    return {
        "geometries": len(areas),
        "olive_parcels": int(areas["n_parcels"].sum()),
        "olive_ha": round(float(areas["olive_ha"].sum()), 1),
        "sampled_ha": round(float(areas["sampled_ha"].sum()), 1),
        "bbox_km2": round(float((east - west) * (north - south) / 1e6), 1),
        "vertices": int(metric.geometry.count_coordinates().sum()),
        "payload_bytes": payload_bytes(areas),
    }


# --------------------------------------------------------------------------------------------
# 2. openEO process
# --------------------------------------------------------------------------------------------


def _ndvi_ndmi(bands: ProcessBuilder) -> ProcessBuilder:
    """Per-pixel callback over the `bands` dimension (order: B04, B08, B11)."""
    red: ProcessBuilder = bands[0]
    nir: ProcessBuilder = bands[1]
    swir: ProcessBuilder = bands[2]
    return array_create([(nir - red) / (nir + red), (nir - swir) / (nir + swir)])


def build_monthly_indices(
    geometries: gpd.GeoDataFrame,
    start_date: str,
    end_date: str,
    *,
    connection: Any = None,
) -> Any:
    """Build (without executing) the openEO process: monthly median NDVI/NDMI per geometry.

    Order matters for quality: mask -> indices per pixel -> monthly median per pixel -> spatial
    mean. Taking the median per pixel before averaging means a cloud on one date cannot drag
    the whole municipality down.

    Args:
        geometries: areas in EPSG:4326 (see `olive_area_by_municipality`).
        start_date: inclusive, "YYYY-MM-DD"; use the first day of a month.
        end_date: exclusive, "YYYY-MM-DD"; use the first day of a month.
        connection: authenticated `openeo.Connection`, or `None` to build the graph offline
            (tests, inspecting the request before paying for it).

    Returns:
        An openEO `VectorCube`: one NDVI and one NDMI value per month and geometry.
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
    invalid: DataCube = (scl != SCL_VEGETATION) & (scl != SCL_NOT_VEGETATED)

    indices = (
        cube.filter_bands([*REFLECTANCE_BANDS])
        .mask(invalid)
        .apply_dimension(dimension="bands", process=_ndvi_ndmi)
        .rename_labels(dimension="bands", target=INDEX_NAMES)
    )
    monthly = indices.aggregate_temporal_period(period="month", reducer="median")

    feature_collection = geometry_payload(geometries)
    size = len(json.dumps(feature_collection, separators=(",", ":")))
    if size > MAX_GEOMETRY_BYTES:
        # Fail locally instead of sending a request the backend will reject with HTTP 413.
        raise ValueError(f"Geometry payload is {size:,} bytes (max {MAX_GEOMETRY_BYTES:,}).")
    return monthly.aggregate_spatial(geometries=feature_collection, reducer="mean")


# --------------------------------------------------------------------------------------------
# 3. Reading and cleaning results
# --------------------------------------------------------------------------------------------


def load_indices_csv(
    csv_path: Path,
    geometries: gpd.GeoDataFrame,
    id_columns: list[str] = AREA_ID_COLUMNS,
) -> pd.DataFrame:
    """Turn the openEO CSV into a tidy table: month, <id columns>, ndvi, ndmi.

    openEO identifies geometries by `feature_index` (row order in the request). Months where
    every pixel was masked come back empty and are kept as NaN, so gaps stay visible.
    """
    raw = pd.read_csv(csv_path)
    by_upper = {c.upper(): c for c in raw.columns}
    missing = [name for name in INDEX_NAMES if name not in by_upper]
    if missing:
        raise ValueError(f"Columns {missing} not found in {list(raw.columns)}")

    tidy = raw.rename(columns={by_upper[name]: name.lower() for name in INDEX_NAMES})
    tidy["month"] = pd.to_datetime(tidy["date"]).dt.tz_localize(None).dt.to_period("M")
    attributes = geometries[id_columns].reset_index(drop=True)
    tidy = tidy.merge(attributes, left_on="feature_index", right_index=True, how="left")
    columns = ["month", *id_columns, "ndvi", "ndmi"]
    return tidy[columns].sort_values([*id_columns, "month"]).reset_index(drop=True)


def hampel_outliers(
    series: pd.Series,
    *,
    window: int = 5,
    n_sigmas: float = 3.0,
    min_deviation: float = 0.05,
    causal: bool = False,
) -> pd.Series:
    """Flag spikes in a time series with a Hampel filter (rolling median +/- k * MAD).

    A value is an outlier when it is far from the median of its neighbours, measured in robust
    standard deviations (1.4826 * MAD). `min_deviation` avoids flagging tiny wiggles in very
    smooth stretches where the MAD is almost zero.

    Example: monthly NDVI ... 0.45, 0.46, 0.08, 0.44 ... -> the 0.08 (a cloudy month) is flagged.

    Centred (default, for exploring a finished series): the first and last valid values are never
    flagged, because a spike needs neighbours on both sides and the start of a series is often a
    genuine seasonal transition (e.g. October, before the autumn rains green up the ground cover).

    `causal=True` (for model features): each month is judged against itself and the previous
    months only, so later images can never change an earlier value. Needed because features stop
    in August and must not be cleaned with September or October images.
    """
    rolling = series.rolling(window, center=not causal, min_periods=3)
    median = rolling.median()
    # nanmedian: months where every pixel was masked are NaN and must not blind the filter.
    mad = rolling.apply(lambda w: float(np.nanmedian(np.abs(w - np.nanmedian(w)))), raw=True)
    deviation = (series - median).abs()
    threshold = np.maximum(n_sigmas * 1.4826 * mad, min_deviation)
    flags = (deviation > threshold).fillna(False).astype(bool)
    valid = np.flatnonzero(series.notna().to_numpy())
    if valid.size and not causal:
        flags.iloc[[valid[0], valid[-1]]] = False
    return flags


def clean_monthly_indices(
    tidy: pd.DataFrame, id_columns: list[str] = AREA_ID_COLUMNS, *, causal: bool = False
) -> pd.DataFrame:
    """Add `<index>_outlier` flags per geometry and `<index>_clean` with outliers set to NaN.

    Outliers are kept in the raw columns (never silently deleted) so they can be inspected.
    `causal=True` uses a trailing window (see `hampel_outliers`); model features need it.
    """
    result = tidy.sort_values([*id_columns, "month"]).copy()
    for name in ("ndvi", "ndmi"):
        flags = result.groupby(id_columns, group_keys=False)[name].apply(
            lambda series: hampel_outliers(series, causal=causal)
        )
        result[f"{name}_outlier"] = flags.reindex(result.index).astype(bool)
        result[f"{name}_clean"] = result[name].mask(result[f"{name}_outlier"])
    return result.reset_index(drop=True)
