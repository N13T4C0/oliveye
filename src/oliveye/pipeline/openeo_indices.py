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
) -> gpd.GeoDataFrame:
    """Dissolve the olive parcels of each municipality into a single geometry for openEO.

    Steps, all in EPSG:25830 (metres):

    1. keep one land use (olive grove by default);
    2. shrink each parcel by one Sentinel-2 pixel (10 m) to drop mixed border pixels;
    3. dissolve per municipality and simplify the outline (5 m is half a pixel, so the set of
       pixels covered barely changes, but the GeoJSON sent to openEO gets much smaller).

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
    dissolved["geometry"] = dissolved.simplify(simplify_tolerance_m, preserve_topology=True)
    dissolved["sampled_ha"] = dissolved.area / 1e4

    areas = dissolved.join(stats).reset_index()
    columns = [*AREA_ID_COLUMNS, "n_parcels", "olive_ha", "sampled_ha", "geometry"]
    return areas[columns].to_crs(OPENEO_CRS)


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

    feature_collection = json.loads(geometries[["geometry"]].to_json())
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
) -> pd.Series:
    """Flag spikes in a time series with a Hampel filter (rolling median +/- k * MAD).

    A value is an outlier when it is far from the median of its neighbours, measured in robust
    standard deviations (1.4826 * MAD). `min_deviation` avoids flagging tiny wiggles in very
    smooth stretches where the MAD is almost zero.

    Example: monthly NDVI ... 0.45, 0.46, 0.08, 0.44 ... -> the 0.08 (a cloudy month) is flagged.
    """
    rolling = series.rolling(window, center=True, min_periods=3)
    median = rolling.median()
    mad = rolling.apply(lambda w: float(np.median(np.abs(w - np.median(w)))), raw=True)
    deviation = (series - median).abs()
    threshold = np.maximum(n_sigmas * 1.4826 * mad, min_deviation)
    return (deviation > threshold).fillna(False).astype(bool)


def clean_monthly_indices(
    tidy: pd.DataFrame, id_columns: list[str] = AREA_ID_COLUMNS
) -> pd.DataFrame:
    """Add `<index>_outlier` flags per geometry and `<index>_clean` with outliers set to NaN.

    Outliers are kept in the raw columns (never silently deleted) so they can be inspected.
    """
    result = tidy.sort_values([*id_columns, "month"]).copy()
    for name in ("ndvi", "ndmi"):
        flags = result.groupby(id_columns, group_keys=False)[name].apply(hampel_outliers)
        result[f"{name}_outlier"] = flags.reindex(result.index).astype(bool)
        result[f"{name}_clean"] = result[name].mask(result[f"{name}_outlier"])
    return result.reset_index(drop=True)
