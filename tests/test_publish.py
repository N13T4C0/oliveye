"""Tests for the helpers that prepare the API's published JSON."""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from oliveye.pipeline.publish import display_name, map_features, records


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Carolina, La", "La Carolina"),
        ("Guardia de Jaén, La", "La Guardia de Jaén"),
        ("Alcalá la Real", "Alcalá la Real"),
        ("Zubia, La", "La Zubia"),
    ],
)
def test_display_name_moves_the_article_to_the_front(raw: str, expected: str) -> None:
    assert display_name(raw) == expected


def test_records_turn_nan_into_null() -> None:
    frame = pd.DataFrame({"a": [1.0, float("nan")], "b": ["x", None]})
    assert records(frame) == [{"a": 1.0, "b": "x"}, {"a": None, "b": None}]


def test_map_features_attach_campaign_indices_to_each_footprint() -> None:
    footprints = gpd.GeoDataFrame(
        {"province_code": ["23"], "municipality_code": ["60"], "olive_ha": [21000.0], "cells": [3]},
        geometry=[box(-4.0, 37.7, -3.9, 37.8)],
        crs="EPSG:4326",
    )
    seasonal = pd.DataFrame(
        {
            "province_code": ["23", "23"],
            "municipality_code": ["60", "60"],
            "campaign": ["2024/25", "2025/26"],
            "ndvi_spring": [0.41, 0.38],
            "ndmi_summer": [-0.05, float("nan")],
        }
    )
    names = {("23", "60"): "Martos"}

    collection = map_features(footprints, seasonal, names, ["ndvi_spring", "ndmi_summer"])

    feature = collection["features"][0]
    assert feature["properties"]["name"] == "Martos"
    assert feature["properties"]["indices"]["2024/25"]["ndvi_spring"] == pytest.approx(0.41)
    assert feature["properties"]["indices"]["2025/26"]["ndmi_summer"] is None
    assert feature["geometry"]["type"] == "Polygon"
