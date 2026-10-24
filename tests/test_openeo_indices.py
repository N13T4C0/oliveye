"""Offline tests for oliveye.pipeline.openeo_indices (no openEO connection, no credits spent)."""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from oliveye.pipeline.openeo_indices import (
    build_monthly_indices,
    clean_monthly_indices,
    hampel_outliers,
    load_indices_csv,
    olive_area_by_municipality,
)
from oliveye.pipeline.openeo_jobs import cache_key

X0, Y0 = 410_000.0, 4_170_000.0  # Martos (Jaén), EPSG:25830


@pytest.fixture
def parcels() -> gpd.GeoDataFrame:
    """Two municipalities: '60' with two olive squares + one arable, '61' with one olive square."""
    geoms = [
        box(X0, Y0, X0 + 200, Y0 + 200),
        box(X0 + 500, Y0, X0 + 700, Y0 + 200),
        box(X0, Y0 + 500, X0 + 100, Y0 + 600),
        box(X0 + 3000, Y0, X0 + 3100, Y0 + 100),
    ]
    gdf = gpd.GeoDataFrame(
        {
            "parcel_id": ["a", "b", "ta", "c"],
            "land_use_code": ["OV", "OV", "TA", "OV"],
            "province_code": ["23"] * 4,
            "municipality_code": ["60", "60", "60", "61"],
        },
        geometry=geoms,
        crs="EPSG:25830",
    )
    gdf["area_ha"] = gdf.area / 1e4
    return gdf


def test_olive_area_dissolves_per_municipality(parcels: gpd.GeoDataFrame) -> None:
    areas = olive_area_by_municipality(parcels)

    assert areas.crs.to_epsg() == 4326
    assert list(areas["municipality_code"]) == ["60", "61"]
    martos = areas.iloc[0]
    assert martos["n_parcels"] == 2  # the arable parcel is excluded
    assert martos["olive_ha"] == pytest.approx(8.0)
    # Each 200 m square shrinks to 180 m after the 10 m inner buffer.
    assert martos["sampled_ha"] == pytest.approx(2 * 180 * 180 / 1e4, rel=1e-3)


def test_olive_area_requires_metric_crs(parcels: gpd.GeoDataFrame) -> None:
    with pytest.raises(ValueError, match="EPSG:25830"):
        olive_area_by_municipality(parcels.to_crs(4326))


def test_process_graph_is_monthly_and_aggregated(parcels: gpd.GeoDataFrame) -> None:
    areas = olive_area_by_municipality(parcels)
    graph = build_monthly_indices(areas, "2025-07-01", "2025-08-01").flat_graph()

    processes = {node["process_id"] for node in graph.values()}
    assert {
        "load_collection",
        "mask",
        "apply_dimension",
        "rename_labels",
        "aggregate_temporal_period",
        "aggregate_spatial",
    } <= processes
    assert graph["loadcollection1"]["arguments"]["bands"] == ["B04", "B08", "B11", "SCL"]
    temporal = graph["aggregatetemporalperiod1"]["arguments"]
    assert temporal["period"] == "month"
    assert graph["renamelabels1"]["arguments"]["target"] == ["NDVI", "NDMI"]
    assert len(graph["aggregatespatial1"]["arguments"]["geometries"]["features"]) == 2


def test_cache_key_changes_with_dates(parcels: gpd.GeoDataFrame) -> None:
    areas = olive_area_by_municipality(parcels)
    a = build_monthly_indices(areas, "2025-07-01", "2025-08-01")
    b = build_monthly_indices(areas, "2025-07-01", "2025-08-01")
    c = build_monthly_indices(areas, "2025-07-01", "2025-09-01")

    assert cache_key(a) == cache_key(b) != cache_key(c)


def test_load_indices_csv_keeps_empty_months(tmp_path: Path, parcels: gpd.GeoDataFrame) -> None:
    areas = olive_area_by_municipality(parcels)
    path = tmp_path / "result.csv"
    path.write_text(
        "date,feature_index,NDVI,NDMI\n2025-07-01T00:00:00Z,0,0.30,0.05\n2025-07-01T00:00:00Z,1,,\n"
    )
    tidy = load_indices_csv(path, areas)

    assert list(tidy.columns) == ["month", "province_code", "municipality_code", "ndvi", "ndmi"]
    assert tidy.loc[0, "month"] == pd.Period("2025-07", "M")
    assert tidy.loc[0, "ndmi"] == pytest.approx(0.05)
    assert np.isnan(tidy.loc[1, "ndvi"])


def test_hampel_flags_a_cloudy_spike_only() -> None:
    values = pd.Series([0.45, 0.46, 0.44, 0.08, 0.45, 0.43, 0.44])
    flags = hampel_outliers(values)

    assert flags.tolist() == [False, False, False, True, False, False, False]


def test_hampel_ignores_smooth_seasonal_change() -> None:
    values = pd.Series(np.linspace(0.48, 0.27, 12))  # winter -> late summer decline
    assert not hampel_outliers(values).any()


def test_clean_keeps_raw_and_masks_outliers() -> None:
    months = pd.period_range("2025-01", periods=7, freq="M")
    tidy = pd.DataFrame(
        {
            "month": list(months) * 2,
            "province_code": ["23"] * 14,
            "municipality_code": ["60"] * 7 + ["61"] * 7,
            "ndvi": [0.45, 0.46, 0.44, 0.08, 0.45, 0.43, 0.44] + [0.40] * 7,
            "ndmi": [0.05] * 14,
        }
    )
    clean = clean_monthly_indices(tidy)

    assert clean["ndvi_outlier"].sum() == 1
    assert clean.loc[3, "ndvi"] == pytest.approx(0.08)  # raw value preserved
    assert np.isnan(clean.loc[3, "ndvi_clean"])
    assert not clean["ndmi_outlier"].any()
