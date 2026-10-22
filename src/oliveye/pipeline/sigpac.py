"""Fetch small subsets of SIGPAC parcels for Andalusia without downloading the full dataset.

Source: SIGPAC 2025 for Andalusia (© Junta de Andalucía), republished as a single GeoParquet
file on source.coop (fiboa "harmonized-field-data" collection, ~4.4M parcels, ~1.8 GB).

DuckDB reads Parquet over HTTP using range requests and row-group statistics, so filtering by
province/municipality/land use only transfers the matching parts of the file. Results are cached
locally: if the output file already exists, nothing is downloaded again.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
from shapely import wkb

SIGPAC_ANDALUSIA_URL = (
    "https://data.source.coop/ftw/harmonized-field-data/es_an/latest/es_an.parquet"
)

# CRS of the source file (ETRS89 / UTM 30N), as documented by the publisher. Kept as-is so that
# areas and distances are in metres; reproject to EPSG:4326 only when storing in PostGIS or mapping.
SOURCE_CRS = "EPSG:25830"

# SIGPAC land-use codes (https://fiboa.org/code/es/sigpac/land_use.csv).
OLIVE_GROVE = "OV"  # pure olive grove
ARABLE_LAND = "TA"  # arable land (cereals, mostly): useful as a phenology contrast
DEFAULT_LAND_USES: tuple[str, ...] = (OLIVE_GROVE, ARABLE_LAND)


@dataclass(frozen=True)
class MunicipalityRanking:
    """Olive-grove surface of one municipality."""

    municipality_code: str
    parcels: int
    olive_hectares: float


def _connect() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB connection.

    The `httpfs` extension (HTTP/S3 reads) is auto-installed and auto-loaded by DuckDB the first
    time an https:// path is queried, so local files work offline and remote ones need no setup.
    """
    return duckdb.connect()


def _code_filter(con: duckdb.DuckDBPyConnection, source: str, column: str) -> str:
    """Return a SQL predicate `column = ?` that matches the column's stored type.

    The publisher may store codes as integers or strings. Comparing with the native type
    (instead of casting the column) keeps Parquet row-group pruning working, so DuckDB can
    skip the parts of the remote file that cannot match.
    """
    schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{source}')").fetchall()
    column_type = next(str(row[1]) for row in schema if row[0] == column)
    if "INT" in column_type.upper():
        return f'"{column}" = CAST(? AS {column_type})'
    return f'CAST("{column}" AS VARCHAR) = CAST(? AS VARCHAR)'


def rank_municipalities_by_olive_area(
    province_code: str,
    *,
    source: str = SIGPAC_ANDALUSIA_URL,
    limit: int = 15,
) -> list[MunicipalityRanking]:
    """List the municipalities of a province with the largest olive-grove (OV) surface.

    Only three light columns are read, never the geometries.
    """
    con = _connect()
    province_filter = _code_filter(con, source, "admin_province_code")
    rows = con.execute(
        f"""
        SELECT CAST(admin_municipality_code AS VARCHAR) AS municipality_code,
               count(*)                                 AS parcels,
               sum("metrics:area") / 1e4                AS olive_hectares
        FROM read_parquet('{source}')
        WHERE {province_filter} AND "crop:code" = ?
        GROUP BY 1
        ORDER BY olive_hectares DESC
        LIMIT ?
        """,
        [province_code, OLIVE_GROVE, limit],
    ).fetchall()
    return [MunicipalityRanking(str(code), int(n), float(ha)) for code, n, ha in rows]


def fetch_municipality_parcels(
    province_code: str,
    municipality_code: str,
    *,
    land_uses: tuple[str, ...] = DEFAULT_LAND_USES,
    source: str = SIGPAC_ANDALUSIA_URL,
) -> gpd.GeoDataFrame:
    """Download the SIGPAC parcels of one municipality for the given land-use codes."""
    con = _connect()
    province_filter = _code_filter(con, source, "admin_province_code")
    municipality_filter = _code_filter(con, source, "admin_municipality_code")
    placeholders = ", ".join("?" for _ in land_uses)

    df: pd.DataFrame = con.execute(
        f"""
        SELECT id                                        AS parcel_id,
               "crop:code"                               AS land_use_code,
               "crop:name"                               AS land_use_name,
               CAST(admin_province_code AS VARCHAR)      AS province_code,
               CAST(admin_municipality_code AS VARCHAR)  AS municipality_code,
               "metrics:area" / 1e4                      AS area_ha,
               geometry
        FROM read_parquet('{source}')
        WHERE {province_filter}
          AND {municipality_filter}
          AND "crop:code" IN ({placeholders})
        """,
        [province_code, municipality_code, *land_uses],
    ).df()

    # DuckDB returns geometries as WKB bytes; decode them into Shapely objects.
    geometries = [wkb.loads(bytes(g)) for g in df.pop("geometry")]
    return gpd.GeoDataFrame(df, geometry=geometries, crs=SOURCE_CRS)


def subset_path(output_dir: Path, province_code: str, municipality_code: str) -> Path:
    """Deterministic file name, so the same request always maps to the same cached file."""
    return output_dir / f"sigpac_2025_{province_code}_{municipality_code}.parquet"


def fetch_and_cache_municipality(
    province_code: str,
    municipality_code: str,
    output_dir: Path,
    *,
    source: str = SIGPAC_ANDALUSIA_URL,
    force: bool = False,
) -> Path:
    """Fetch a municipality subset and save it as GeoParquet, reusing the cached file if present."""
    path = subset_path(output_dir, province_code, municipality_code)
    if path.exists() and not force:
        return path

    parcels = fetch_municipality_parcels(province_code, municipality_code, source=source)
    if parcels.empty:
        raise ValueError(
            f"No parcels found for province={province_code}, municipality={municipality_code}. "
            "Run the ranking first to get valid municipality codes."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    parcels.to_parquet(path)
    return path
