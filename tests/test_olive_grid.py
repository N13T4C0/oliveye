"""Offline tests for the olive-dominant grid."""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from oliveye.pipeline.olive_grid import (
    aggregate_cells,
    grid_summary,
    municipality_footprints,
    olive_grid_cells,
)

X0, Y0 = 410_000, 4_170_000  # multiples of 250 m, Martos (EPSG:25830)


def make_parcels() -> gpd.GeoDataFrame:
    """Cell A: full olive. Cell B: 60 % olive. Cell C: arable only. One olive cell in muni 61."""
    geoms = [
        box(X0, Y0, X0 + 250, Y0 + 250),  # A: 100 % olive, muni 60
        box(X0 + 250, Y0, X0 + 400, Y0 + 250),  # B: 60 % olive, muni 60
        box(X0 + 500, Y0, X0 + 750, Y0 + 250),  # C: arable
        box(X0, Y0 + 250, X0 + 250, Y0 + 500),  # D: 100 % olive, muni 61
    ]
    gdf = gpd.GeoDataFrame(
        {
            "parcel_id": ["a", "b", "c", "d"],
            "land_use_code": ["OV", "OV", "TA", "OV"],
            "province_code": ["23"] * 4,
            "municipality_code": ["60", "60", "60", "61"],
        },
        geometry=geoms,
        crs="EPSG:25830",
    )
    gdf["area_ha"] = gdf.area / 1e4
    return gdf


def test_keeps_only_olive_dominant_cells() -> None:
    cells = olive_grid_cells(make_parcels())

    assert list(cells["cell_id"]) == [f"E{X0}N{Y0}", f"E{X0}N{Y0 + 250}"]
    assert list(cells["municipality_code"]) == ["60", "61"]
    assert cells["olive_share"].tolist() == pytest.approx([1.0, 1.0])
    assert cells["olive_ha"].tolist() == pytest.approx([6.25, 6.25])


def test_threshold_is_configurable() -> None:
    cells = olive_grid_cells(make_parcels(), min_olive_share=0.5)
    assert f"E{X0 + 250}N{Y0}" in set(cells["cell_id"])  # the 60 % cell now qualifies


def test_cell_size_must_follow_the_sentinel2_grid() -> None:
    with pytest.raises(ValueError, match="multiple of 10"):
        olive_grid_cells(make_parcels(), cell_m=255)


def test_summary_reports_coverage() -> None:
    parcels = make_parcels()
    cells = olive_grid_cells(parcels)
    summary = grid_summary(cells, parcels)

    olive_total = 6.25 + 3.75 + 6.25
    assert summary["cells"] == 2
    assert summary["coverage_pct"] == pytest.approx(round(100 * 12.5 / olive_total, 1))


def test_aggregate_is_area_weighted_and_skips_gaps() -> None:
    cells = gpd.GeoDataFrame(
        {
            "cell_id": ["a", "b", "c"],
            "province_code": ["23"] * 3,
            "municipality_code": ["60"] * 3,
            "olive_ha": [6.0, 2.0, 4.0],
        },
        geometry=[box(0, 0, 1, 1)] * 3,
        crs="EPSG:25830",
    )
    month = pd.Period("2025-07", "M")
    tidy = pd.DataFrame(
        {
            "month": [month] * 3,
            "cell_id": ["a", "b", "c"],
            "ndvi": [0.4, 0.8, np.nan],  # cell c fully clouded this month
            "ndmi": [0.1, 0.1, 0.1],
        }
    )
    result = aggregate_cells(tidy, cells)

    assert result.loc[0, "ndvi"] == pytest.approx((0.4 * 6 + 0.8 * 2) / 8)
    assert result.loc[0, "ndmi"] == pytest.approx(0.1)
    assert result.loc[0, "valid_cells"] == 2


def test_footprints_dissolve_cells_per_municipality() -> None:
    """Adjacent cells of one municipality become one polygon; area kept; output in EPSG:4326."""
    cells = gpd.GeoDataFrame(
        {
            "province_code": ["23", "23", "23"],
            "municipality_code": ["60", "60", "61"],
            "olive_ha": [6.0, 6.0, 5.0],
        },
        geometry=[
            box(400000, 4170000, 400250, 4170250),
            box(400250, 4170000, 400500, 4170250),  # touches the first one
            box(410000, 4170000, 410250, 4170250),
        ],
        crs="EPSG:25830",
    ).to_crs("EPSG:4326")

    footprints = municipality_footprints(cells, simplify_m=10)

    assert footprints.crs.to_epsg() == 4326
    assert len(footprints) == 2
    martos = footprints[footprints["municipality_code"] == "60"].iloc[0]
    assert martos.geometry.geom_type == "Polygon"
    assert martos["olive_ha"] == pytest.approx(12.0)
    assert martos["cells"] == 2
    area_ha = footprints.to_crs("EPSG:25830").area.iloc[0] / 1e4
    assert area_ha == pytest.approx(12.5, rel=0.02)  # 2 cells of 6.25 ha
