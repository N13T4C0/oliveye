"""Helpers that turn pipeline outputs into the small JSON files the API publishes."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from typing import Any

import geopandas as gpd
import pandas as pd

_ARTICLES = ("La", "El", "Las", "Los")


def display_name(name: str) -> str:
    """INE writes 'Carolina, La'; people write 'La Carolina'."""
    head, sep, tail = name.rpartition(", ")
    if sep and tail in _ARTICLES:
        return f"{tail} {head}"
    return name


def _clean(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if value is pd.NA or value is pd.NaT:
        return None
    return value


def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Rows as JSON-ready dicts: NaN becomes null (never an invented value)."""
    return [
        {str(key): _clean(value) for key, value in row.items()}
        for row in frame.astype(object).to_dict("records")
    ]


def map_features(
    footprints: gpd.GeoDataFrame,
    seasonal: pd.DataFrame,
    names: dict[tuple[str, str], str],
    columns: Sequence[str],
    *,
    precision: int = 5,
) -> dict[str, Any]:
    """GeoJSON FeatureCollection: footprint geometry + name + seasonal indices per campaign.

    `precision=5` decimals is ~1 m, far below the 60 m simplification: smaller files, same map.
    """
    keys = ["province_code", "municipality_code"]
    by_municipality: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in records(seasonal[[*keys, "campaign", *columns]]):
        key = (str(row["province_code"]), str(row["municipality_code"]))
        by_municipality.setdefault(key, {})[str(row["campaign"])] = {c: row[c] for c in columns}

    geojson = json.loads(footprints.to_crs("EPSG:4326").to_json(to_wgs84=True))
    for feature in geojson["features"]:
        props = feature["properties"]
        key = (str(props["province_code"]), str(props["municipality_code"]))
        props["name"] = names.get(key, key[1])
        props["olive_ha"] = round(float(props["olive_ha"]), 1)
        props["indices"] = by_municipality.get(key, {})
        feature["geometry"] = _round_geometry(feature["geometry"], precision)
    geojson.pop("crs", None)
    return {"type": "FeatureCollection", "features": geojson["features"]}


def _round_geometry(geometry: dict[str, Any], precision: int) -> dict[str, Any]:
    def walk(coords: Any) -> Any:
        if isinstance(coords, list | tuple) and coords and isinstance(coords[0], int | float):
            return [round(float(c), precision) for c in coords]
        return [walk(c) for c in coords]

    return {"type": geometry["type"], "coordinates": walk(geometry["coordinates"])}
