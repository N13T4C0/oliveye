"""Offline tests for the RIA parsers (sample payloads, no network)."""

import json

import pandas as pd
import pytest

from oliveye.pipeline.climate import (
    daily_url,
    dms_to_decimal,
    open_meteo_url,
    parse_daily,
    parse_open_meteo,
    parse_stations,
)


def test_parse_stations() -> None:
    payload = json.dumps(
        [
            {
                "provincia": {"id": 23, "nombre": "Jaén"},
                "codigoEstacion": 7,
                "nombre": "Mancha Real",
                "altitud": 430,
                "latitud": "37º55'31''N",
                "longitud": "03º36'43''W",
                "bajoplastico": False,
            }
        ]
    )
    table = parse_stations(payload)
    assert table.loc[0, "province_id"] == 23 and table.loc[0, "station_code"] == 7


def test_parse_daily_renames_and_sorts() -> None:
    payload = json.dumps(
        [
            {"fecha": "2022-05-02", "tempMax": 33.1, "tempMin": 14.0, "precipitacion": 0.0},
            {"fecha": "2022-05-01", "tempMax": 36.4, "tempMin": 16.2, "precipitacion": 0.0},
        ]
    )
    table = parse_daily(payload, 23, 7)
    assert list(table.columns) == [
        "province_id",
        "station_code",
        "date",
        "tmax_c",
        "tmin_c",
        "precip_mm",
    ]
    assert table.loc[0, "date"] == pd.Timestamp("2022-05-01")
    assert table.loc[0, "tmax_c"] == pytest.approx(36.4)


def test_daily_url() -> None:
    assert daily_url(23, 7, "2022-05-01", "2022-05-31").endswith(
        "/datosdiarios/forceEt0/23/7/2022-05-01/2022-05-31"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [("37º55'31''N", 37.925278), ("03º36'43''W", -3.611944), ("03º36'43''O", -3.611944)],
)
def test_dms_to_decimal(text: str, expected: float) -> None:
    assert dms_to_decimal(text) == pytest.approx(expected, abs=1e-5)


def test_open_meteo_url_and_parse_multi_point() -> None:
    url = open_meteo_url([37.72, 38.01], [-3.97, -3.37], "2022-05-01", "2022-05-02")
    assert "latitude=37.7200%2C38.0100" in url and "daily=temperature_2m_max" in url

    one = {
        "daily": {
            "time": ["2022-05-01", "2022-05-02"],
            "temperature_2m_max": [36.1, 34.0],
            "temperature_2m_min": [15.0, 14.2],
            "precipitation_sum": [0.0, 0.0],
            "et0_fao_evapotranspiration": [6.1, 5.8],
        }
    }
    table = parse_open_meteo(json.dumps([one, one]), ["23-60", "23-92"])
    assert list(table["point_id"].unique()) == ["23-60", "23-92"]
    assert table.loc[0, "tmax_c"] == pytest.approx(36.1)
    with pytest.raises(ValueError, match="Expected 3 locations"):
        parse_open_meteo(json.dumps([one, one]), ["a", "b", "c"])
