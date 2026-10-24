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


# --------------------------------------------------------------------------------------------
# Open-Meteo historical weather (ERA5 reanalysis), the keyless fallback when RIA is unreachable
# --------------------------------------------------------------------------------------------

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_DAILY = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
)
OPEN_METEO_COLUMNS = {
    "temperature_2m_max": "tmax_c",
    "temperature_2m_min": "tmin_c",
    "precipitation_sum": "precip_mm",
    "et0_fao_evapotranspiration": "et0_mm",
}


def open_meteo_url(latitudes: list[float], longitudes: list[float], start: str, end: str) -> str:
    """Archive API URL for several points at once (daily values, Europe/Madrid days)."""
    from urllib.parse import urlencode

    query = urlencode(
        {
            "latitude": ",".join(f"{v:.4f}" for v in latitudes),
            "longitude": ",".join(f"{v:.4f}" for v in longitudes),
            "start_date": start,
            "end_date": end,
            "daily": ",".join(OPEN_METEO_DAILY),
            "timezone": "Europe/Madrid",
        }
    )
    return f"{OPEN_METEO_ARCHIVE_URL}?{query}"


def parse_open_meteo(payload: str, point_ids: list[str]) -> pd.DataFrame:
    """Tidy daily table (point_id, date, tmax_c, tmin_c, precip_mm, et0_mm).

    The API returns one object for a single point and a list for several points, in the order
    of the requested coordinates.
    """
    data = json.loads(payload)
    locations = data if isinstance(data, list) else [data]
    if len(locations) != len(point_ids):
        raise ValueError(f"Expected {len(point_ids)} locations, got {len(locations)}")
    frames = []
    for point_id, location in zip(point_ids, locations, strict=True):
        daily = pd.DataFrame(location["daily"]).rename(
            columns={"time": "date", **OPEN_METEO_COLUMNS}
        )
        daily["date"] = pd.to_datetime(daily["date"])
        daily.insert(0, "point_id", point_id)
        frames.append(daily)
    return pd.concat(frames, ignore_index=True)
