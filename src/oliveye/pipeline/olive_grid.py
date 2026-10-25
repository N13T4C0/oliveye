"""Olive-dominant grid cells: the sampling unit sent to openEO.

Why a grid instead of parcel outlines (see ADR 0001, addendum):

* **Request size.** Martos alone has ~18,000 olive parcels; their dissolved outline is a ~3 MB
  GeoJSON that CDSE rejects with HTTP 413, and simplifying it enough loses >25 % of the area.
  A 250 m cell is a square with 5 vertices: ~1,000 cells weigh ~150 KB.
* **Pure pixels.** Only cells that are at least `min_olive_share` olive grove are kept, so the
  index measures olive trees, not the roads, villages and cereal fields around them.
* **Alignment.** Cell edges are multiples of 250 m in EPSG:25830, i.e. multiples of 10 m, so
  they coincide with Sentinel-2 pixel edges (UTM zone 30N grid) and no pixel is split.
* **Map-ready.** Results per cell can be drawn on the web map; municipality values are the
  olive-area-weighted mean of their cells.

Example: a 250 m cell (6.25 ha) with 5.4 ha of olive parcels has an olive share of 0.86 and is
kept; a cell half olive, half village (share 0.5) is discarded.
"""

from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from oliveye.pipeline.sigpac import OLIVE_GROVE

METRIC_CRS = "EPSG:25830"
DEFAULT_CELL_M = 250
DEFAULT_MIN_OLIVE_SHARE = 0.8
CELL_COLUMNS = [
    "cell_id",
    "province_code",
    "municipality_code",
    "olive_ha",
    "olive_share",
    "geometry",
]


def _grid(bounds: tuple[float, float, float, float], cell_m: int) -> gpd.GeoDataFrame:
    """Square cells covering `bounds`, snapped to multiples of `cell_m` (EPSG:25830)."""
    west, south, east, north = bounds
    x0, y0 = math.floor(west / cell_m) * cell_m, math.floor(south / cell_m) * cell_m
    xs = np.arange(x0, east, cell_m)
    ys = np.arange(y0, north, cell_m)
    cells = [(int(x), int(y), box(x, y, x + cell_m, y + cell_m)) for x in xs for y in ys]
    return gpd.GeoDataFrame(
        {
            # Stable id from the lower-left corner: same cell -> same id in every run.
            "cell_id": [f"E{x}N{y}" for x, y, _ in cells],
        },
        geometry=[geom for _, _, geom in cells],
        crs=METRIC_CRS,
    )


def olive_grid_cells(
    parcels: gpd.GeoDataFrame,
    *,
    cell_m: int = DEFAULT_CELL_M,
    min_olive_share: float = DEFAULT_MIN_OLIVE_SHARE,
    land_use_code: str = OLIVE_GROVE,
) -> gpd.GeoDataFrame:
    """Grid cells where olive grove covers at least `min_olive_share` of the cell.

    Args:
        parcels: SIGPAC parcels in EPSG:25830 with `land_use_code`, `province_code` and
            `municipality_code`.
        cell_m: cell side in metres; keep it a multiple of 10 to stay on the Sentinel-2 grid.
        min_olive_share: minimum fraction of the cell covered by olive parcels (0-1).

    Returns:
        One row per kept cell (EPSG:25830). A cell spanning two municipalities is assigned to
        the one with more olive area inside it.
    """
    if parcels.crs is None or parcels.crs.to_string() != METRIC_CRS:
        raise ValueError(f"Parcels must be in {METRIC_CRS} to build a metric grid.")
    if cell_m % 10:
        raise ValueError("cell_m must be a multiple of 10 m to align with Sentinel-2 pixels.")

    olive = parcels.loc[
        parcels["land_use_code"] == land_use_code,
        ["province_code", "municipality_code", "geometry"],
    ]
    if olive.empty:
        raise ValueError(f"No parcels with land use '{land_use_code}'.")

    grid = _grid(tuple(olive.total_bounds), cell_m)
    pieces = gpd.overlay(grid, olive, how="intersection", keep_geom_type=True)
    pieces["olive_ha"] = pieces.area / 1e4

    per_municipality = (
        pieces.groupby(["cell_id", "province_code", "municipality_code"], as_index=False)[
            "olive_ha"
        ]
        .sum()
        .sort_values("olive_ha", ascending=False)
    )
    totals = per_municipality.groupby("cell_id")["olive_ha"].sum()
    owner = per_municipality.drop_duplicates("cell_id").set_index("cell_id")

    cell_ha = cell_m * cell_m / 1e4
    table = pd.DataFrame(
        {
            "province_code": owner["province_code"],
            "municipality_code": owner["municipality_code"],
            "olive_ha": totals,
            "olive_share": (totals / cell_ha).clip(upper=1.0),
        }
    )
    table = table[table["olive_share"] >= min_olive_share]

    cells = grid.set_index("cell_id").join(table, how="inner").reset_index()
    cells = cells.sort_values("cell_id").reset_index(drop=True)
    return gpd.GeoDataFrame(cells[CELL_COLUMNS], geometry="geometry", crs=METRIC_CRS)


def grid_summary(cells: gpd.GeoDataFrame, parcels: gpd.GeoDataFrame) -> dict[str, float | int]:
    """How much of the municipality's olive grove the kept cells represent."""
    olive_total_ha = float(parcels.loc[parcels["land_use_code"] == OLIVE_GROVE, "area_ha"].sum())
    sampled_ha = float(cells["olive_ha"].sum())
    west, south, east, north = cells.to_crs(METRIC_CRS).total_bounds
    return {
        "cells": len(cells),
        "olive_ha_total": round(olive_total_ha, 1),
        "olive_ha_in_cells": round(sampled_ha, 1),
        "coverage_pct": round(100 * sampled_ha / olive_total_ha, 1) if olive_total_ha else 0.0,
        "mean_olive_share": round(float(cells["olive_share"].mean()), 3),
        "bbox_km2": round(float((east - west) * (north - south) / 1e6), 1),
    }


def aggregate_cells(
    tidy_cells: pd.DataFrame,
    cells: gpd.GeoDataFrame,
    group_columns: tuple[str, ...] = ("province_code", "municipality_code"),
) -> pd.DataFrame:
    """Olive-area-weighted mean of the cell indices per municipality and month.

    Cells with no valid observation in a month (all pixels masked) are left out of that month's
    mean; `valid_cells` says how many contributed, so thin months can be spotted.
    """
    weights = cells[["cell_id", *group_columns, "olive_ha"]]
    data = tidy_cells.merge(weights, on="cell_id", how="inner")
    rows = []
    for keys, group in data.groupby(["month", *group_columns]):
        row: dict[str, object] = dict(zip(["month", *group_columns], keys, strict=True))
        for index in ("ndvi", "ndmi"):
            valid = group[group[index].notna()]
            total = valid["olive_ha"].sum()
            row[index] = (valid[index] * valid["olive_ha"]).sum() / total if total else np.nan
        row["valid_cells"] = int(group["ndvi"].notna().sum())
        rows.append(row)
    result = pd.DataFrame(rows)
    return result.sort_values([*group_columns, "month"]).reset_index(drop=True)


def municipality_footprints(
    cells: gpd.GeoDataFrame,
    *,
    simplify_m: float = 60.0,
    group_columns: tuple[str, ...] = ("province_code", "municipality_code"),
) -> gpd.GeoDataFrame:
    """One (multi)polygon per municipality: the olive cells we measured, dissolved for a map.

    Dissolving merges touching cells into one shape; simplifying removes vertices that are
    invisible at map scale (`simplify_m`, in metres). Both run in EPSG:25830 (metres); the result
    is returned in EPSG:4326, the storage CRS. Example: Martos' 3,130 cells become one shape.
    """
    metric = cells.to_crs(METRIC_CRS)
    dissolved = metric.dissolve(by=list(group_columns), aggfunc={"olive_ha": "sum"})
    dissolved["cells"] = metric.groupby(list(group_columns)).size()
    dissolved["geometry"] = dissolved.geometry.buffer(0).simplify(
        simplify_m, preserve_topology=True
    )
    return dissolved.reset_index().to_crs("EPSG:4326")
