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
    olive_area_within_budget,
    payload_bytes,
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


def test_hampel_still_works_next_to_a_data_gap() -> None:
    values = pd.Series([0.45, np.nan, 0.08, 0.44, 0.45, 0.43, 0.44])
    assert hampel_outliers(values).tolist()[2] is True


def test_hampel_never_flags_the_series_edges() -> None:
    # Real Martos 2024/25: October (0.355) precedes the autumn green-up; it is not a cloud.
    values = pd.Series([0.355, 0.462, 0.459, 0.444, 0.449, 0.415, 0.404])
    assert not hampel_outliers(values).any()


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


def _mixed_parcels() -> gpd.GeoDataFrame:
    """200 large (150 m) and 200 small (60 m) olive squares, all separate."""
    geoms = []
    for i in range(400):
        side = 150 if i % 2 == 0 else 60
        x, y = X0 + (i % 20) * 200, Y0 + (i // 20) * 200
        geoms.append(box(x, y, x + side, y + side))
    gdf = gpd.GeoDataFrame(
        {
            "parcel_id": [f"p{i}" for i in range(400)],
            "land_use_code": "OV",
            "province_code": "23",
            "municipality_code": "60",
        },
        geometry=geoms,
        crs="EPSG:25830",
    )
    gdf["area_ha"] = gdf.area / 1e4
    return gdf


def test_dropping_small_parts_keeps_large_ones(parcels: gpd.GeoDataFrame) -> None:
    full = olive_area_by_municipality(parcels)
    coarse = olive_area_by_municipality(parcels, min_part_ha=2.0)
    # Municipality 60 keeps its two 3.24 ha squares; 61 (0.64 ha) has nothing left.
    assert coarse.iloc[0]["sampled_ha"] == pytest.approx(full.iloc[0]["sampled_ha"])
    assert list(coarse["municipality_code"]) == ["60"]


def test_budget_drops_small_fragments_until_it_fits() -> None:
    heavy = _mixed_parcels()
    detailed = payload_bytes(olive_area_by_municipality(heavy))

    areas, settings = olive_area_within_budget(heavy, max_bytes=int(detailed * 0.75))

    # After the 10 m inner buffer the small squares are 0.16 ha: dropped at the (30, 0.25) step.
    assert settings["min_part_ha"] == 0.25
    assert settings["payload_bytes"] <= detailed * 0.75
    assert 0 < settings["area_loss_pct"] < 25


def test_budget_never_trades_away_the_olive_grove() -> None:
    with pytest.raises(ValueError, match="without losing more than"):
        olive_area_within_budget(_mixed_parcels(), max_bytes=100)


def test_causal_hampel_never_looks_at_later_months() -> None:
    """Changing months after t must not change the flag at t (features stop at August)."""
    base = pd.Series([0.45, 0.46, 0.44, 0.45, 0.08, 0.45, 0.43, 0.44])
    flags = hampel_outliers(base, causal=True)
    assert flags.iloc[4]  # the cloudy spike is still caught from its past alone
    for t in range(len(base)):
        future_changed = base.copy()
        future_changed.iloc[t + 1 :] = 0.9
        assert hampel_outliers(future_changed, causal=True).iloc[t] == flags.iloc[t]


def test_clean_monthly_indices_can_run_causally() -> None:
    months = pd.period_range("2022-01", periods=8, freq="M")
    tidy = pd.DataFrame(
        {
            "month": months,
            "province_code": "23",
            "municipality_code": "60",
            "ndvi": [0.45, 0.46, 0.44, 0.45, 0.08, 0.45, 0.43, 0.44],
            "ndmi": [0.0] * 8,
        }
    )
    clean = clean_monthly_indices(tidy, causal=True)
    assert np.isnan(clean.loc[4, "ndvi_clean"])
    assert not clean["ndmi_outlier"].any()
