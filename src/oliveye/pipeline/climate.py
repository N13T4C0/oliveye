"""Daily weather from RIA, the agroclimatic station network of the Junta de Andalucía.

RIA (Red de Información Agroclimática de Andalucía, run by IFAPA) has ~100 stations placed in
farmland, many of them among olive groves, and a public JSON web service (no key):

* stations: ``/riaws/estaciones``
* daily data: ``/riaws/datosdiarios/forceEt0/{province}/{station}/{start}/{end}``

Why it matters for olives: a heat wave during flowering (May) can ruin a harvest that looks
perfectly green from space, as in campaign 2022/23. Daily maxima let us count hot days in May.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

RIA_BASE_URL = "https://www.juntadeandalucia.es/agriculturaypesca/ifapa/riaws"

# RIA field -> our column name (only the fields we use; others are dropped).
DAILY_FIELDS: dict[str, str] = {
    "fecha": "date",
    "tempMax": "tmax_c",
    "tempMin": "tmin_c",
    "tempMedia": "tmean_c",
    "precipitacion": "precip_mm",
    "et0": "et0_mm",
    "humedadMedia": "rh_mean_pct",
}


def stations_url() -> str:
    return f"{RIA_BASE_URL}/estaciones"


def daily_url(province_id: int, station_code: int, start: str, end: str) -> str:
    """URL of daily data for one station between two ISO dates (inclusive)."""
    return f"{RIA_BASE_URL}/datosdiarios/forceEt0/{province_id}/{station_code}/{start}/{end}"


def parse_stations(payload: str) -> pd.DataFrame:
    """Station list: province, code, name, altitude and raw coordinates (DMS strings)."""
    records: list[dict[str, Any]] = json.loads(payload)
    rows = [
        {
            "province_id": int(r["provincia"]["id"]),
            "province": r["provincia"].get("nombre", ""),
            "station_code": int(r["codigoEstacion"]),
            "name": r.get("nombre", ""),
            "altitude_m": r.get("altitud"),
            "latitude_raw": r.get("latitud", ""),
            "longitude_raw": r.get("longitud", ""),
            "under_plastic": bool(r.get("bajoplastico", False)),
        }
        for r in records
    ]
    return pd.DataFrame(rows)


def parse_daily(payload: str, province_id: int, station_code: int) -> pd.DataFrame:
    """Daily records of one station with tidy column names and a proper date column."""
    records: list[dict[str, Any]] = json.loads(payload)
    table = pd.DataFrame(records)
    keep = [field for field in DAILY_FIELDS if field in table.columns]
    table = table[keep].rename(columns=DAILY_FIELDS)
    table["date"] = pd.to_datetime(table["date"]).dt.tz_localize(None).dt.normalize()
    table.insert(0, "station_code", station_code)
    table.insert(0, "province_id", province_id)
    return table.sort_values("date").reset_index(drop=True)


def dms_to_decimal(text: str) -> float:
    """'37º46\\'12\\'\\'N' or '03º47\\'00\\'\\'W' -> decimal degrees (W and S negative)."""
    import re

    numbers = [float(n) for n in re.findall(r"\d+(?:[.,]\d+)?", text.replace(",", "."))]
    if not numbers:
        raise ValueError(f"No coordinates in {text!r}")
    degrees, minutes, seconds = (numbers + [0.0, 0.0])[:3]
    value = degrees + minutes / 60 + seconds / 3600
    return -value if text.strip()[-1:].upper() in ("W", "S", "O") else value
