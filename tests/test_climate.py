"""Offline tests for the RIA parsers (sample payloads, no network)."""

import json

import pandas as pd
import pytest

from oliveye.pipeline.climate import daily_url, dms_to_decimal, parse_daily, parse_stations


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
