"""Load the published OlivEye data into PostgreSQL + PostGIS.

Source: the small JSON files the API serves (`api/data/`, built by `scripts/export_api_data.py`),
so the database can be rebuilt anywhere from the repository alone, without the results branch.

Design:

* The schema is plain SQL (`db/init/01_schema.sql`), versioned with the code and idempotent; the
  same file runs when the Docker volume is first created and on every load.
* A load is **one transaction**: tables are emptied and refilled, so a failed load leaves the
  previous data untouched and running it twice gives the same result.
* Geometries are written in EPSG:4326 (the storage CRS) and checked with `ST_IsValid`; areas are
  only ever computed in EPSG:25830 (see the `v_olive_area_check` view).

Example:

    engine = create_engine("postgresql+psycopg://oliveye:***@localhost:5432/oliveye")
    counts = load_all(engine, Path("api/data"))   # {"municipality": 269, ...}
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import URL, Engine, text
from sqlalchemy.engine import Connection

STORAGE_CRS = "EPSG:4326"
PROVINCE_CODES = {"Jaén": "23", "Granada": "18"}  # INE codes, as in SIGPAC
SCHEMA = "oliveye"
# The SQL lives at the repository root (db/init/), next to docker-compose.yml.
SCHEMA_DIR = Path(__file__).resolve().parents[3] / "db" / "init"
# Parents before children, so foreign keys hold while filling.
TABLES = ("municipality", "olive_area", "monthly_index", "production")


def database_url(env: Mapping[str, str] | None = None) -> str:
    """SQLAlchemy URL from `DATABASE_URL`, or from the POSTGRES_* variables of `.env.example`."""
    env = os.environ if env is None else env
    if env.get("DATABASE_URL"):
        return env["DATABASE_URL"]
    password = env.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("Set DATABASE_URL or POSTGRES_PASSWORD (see .env.example).")
    url = URL.create(
        "postgresql+psycopg",
        username=env.get("POSTGRES_USER", "oliveye"),
        password=password,  # URL.create escapes characters such as @ : / # in passwords
        host=env.get("POSTGRES_HOST", "localhost"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        database=env.get("POSTGRES_DB", "oliveye"),
    )
    return url.render_as_string(hide_password=False)


def apply_schema(connection: Connection, schema_dir: Path = SCHEMA_DIR) -> None:
    """Run every `db/init/*.sql` file in name order (they are idempotent).

    The driver treats `%` as a parameter marker, so the SQL files avoid it (comments included).
    `CREATE TABLE IF NOT EXISTS` leaves existing tables untouched: there are no migrations yet,
    so a column change needs a fresh volume (`docker compose down -v`) or a migration tool.
    """
    paths = sorted(schema_dir.glob("*.sql"))
    if not paths:
        raise FileNotFoundError(f"No schema files in {schema_dir}")
    for path in paths:
        connection.exec_driver_sql(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------
# JSON -> tables
# --------------------------------------------------------------------------------------------


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def municipalities_frame(data_dir: Path) -> pd.DataFrame:
    rows = _read(data_dir / "municipalities.json")
    return pd.DataFrame(rows).rename(columns={"olive_hectares": "olive_ha_sigpac"})[
        ["province_code", "municipality_code", "name", "olive_ha_sigpac", "processed"]
    ]


def olive_area_frame(data_dir: Path) -> gpd.GeoDataFrame:
    """Measured olive area per municipality, as MultiPolygons in EPSG:4326."""
    frame = gpd.read_file(data_dir / "map.geojson")
    if frame.crs is None:  # RFC 7946 GeoJSON is always WGS 84
        frame = frame.set_crs(STORAGE_CRS)
    frame = frame.to_crs(STORAGE_CRS)
    frame["geometry"] = [
        MultiPolygon([geom]) if isinstance(geom, Polygon) else geom for geom in frame.geometry
    ]
    columns = ["province_code", "municipality_code", "olive_ha", "cells", "geometry"]
    return frame[columns].rename_geometry("geom")


def monthly_index_frame(data_dir: Path) -> pd.DataFrame:
    """One row per municipality and month; `month` becomes the first day of the month."""
    series: dict[str, list[dict[str, Any]]] = _read(data_dir / "indices.json")
    frames = []
    for key, rows in series.items():
        province, municipality = key.split("-", 1)
        frame = pd.DataFrame(rows)
        frame.insert(0, "municipality_code", municipality)
        frame.insert(0, "province_code", province)
        frames.append(frame)
    table = pd.concat(frames, ignore_index=True)
    table["month"] = pd.PeriodIndex(table["month"], freq="M").to_timestamp().date
    table["valid_cells"] = table["valid_cells"].astype("Int64")
    return table[["province_code", "municipality_code", "month", "ndvi", "ndmi", "valid_cells"]]


def production_frame(data_dir: Path) -> pd.DataFrame:
    series: dict[str, list[dict[str, Any]]] = _read(data_dir / "production.json")
    rows = [
        {"province": province, **point} for province, points in series.items() for point in points
    ]
    frame = pd.DataFrame(rows)
    frame.insert(1, "province_code", frame["province"].map(PROVINCE_CODES))
    if frame["province_code"].isna().any():
        raise ValueError(f"Unknown province in production.json: {set(frame['province'])}")
    columns = ["province", "province_code", "campaign", "oil_final_t", "oil_aforo_t", "pred_t"]
    return frame[[*columns, "target_method"]]


# --------------------------------------------------------------------------------------------
# Load
# --------------------------------------------------------------------------------------------


def load_all(engine: Engine, data_dir: Path, schema_dir: Path = SCHEMA_DIR) -> dict[str, int]:
    """Replace the content of every table with `data_dir`, atomically. Returns rows per table."""
    frames: dict[str, pd.DataFrame] = {
        "municipality": municipalities_frame(data_dir),
        "olive_area": olive_area_frame(data_dir),
        "monthly_index": monthly_index_frame(data_dir),
        "production": production_frame(data_dir),
    }
    with engine.begin() as connection:  # one transaction: all or nothing
        apply_schema(connection, schema_dir)
        tables = ", ".join(f"{SCHEMA}.{name}" for name in TABLES)
        connection.execute(text(f"TRUNCATE {tables}"))
        for name in TABLES:
            frame = frames[name]
            if isinstance(frame, gpd.GeoDataFrame):
                frame.to_postgis(name, connection, schema=SCHEMA, if_exists="append", index=False)
            else:
                frame.to_sql(name, connection, schema=SCHEMA, if_exists="append", index=False)
        invalid = connection.execute(
            text(f"SELECT count(*) FROM {SCHEMA}.olive_area WHERE NOT ST_IsValid(geom)")
        ).scalar_one()
        if invalid:
            raise ValueError(f"{invalid} invalid geometries in olive_area; load rolled back.")
    return {name: len(frame) for name, frame in frames.items()}


def area_check(engine: Engine) -> pd.DataFrame:
    """Measured area per municipality recomputed by PostGIS in EPSG:25830 (metres)."""
    query = f"SELECT * FROM {SCHEMA}.v_olive_area_check ORDER BY province_code, municipality_code"
    with engine.connect() as connection:
        return pd.read_sql(text(query), connection)
