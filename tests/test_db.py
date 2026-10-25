"""PostGIS loader against a real database (skipped unless OLIVEYE_TEST_DATABASE_URL is set).

Locally, with `docker compose up -d` running:

    export OLIVEYE_TEST_DATABASE_URL=postgresql+psycopg://oliveye:<pw>@localhost:5432/oliveye
    uv run --extra db pytest tests/test_db.py

The tests drop and recreate the `oliveye` schema: use a scratch database.
CI runs it against a `postgis/postgis:17-3.5` service container.
"""

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("geoalchemy2", reason="install the 'db' extra to run PostGIS tests")
URL = os.environ.get("OLIVEYE_TEST_DATABASE_URL")
if not URL:
    pytest.skip("OLIVEYE_TEST_DATABASE_URL not set", allow_module_level=True)

from sqlalchemy import create_engine, text  # noqa: E402

from oliveye.db.load import area_check, database_url, load_all  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "api" / "data"


@pytest.fixture(scope="module")
def engine():  # type: ignore[no-untyped-def]
    engine = create_engine(URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS oliveye CASCADE"))
    yield engine
    engine.dispose()


def test_load_counts_match_the_published_files(engine) -> None:  # type: ignore[no-untyped-def]
    counts = load_all(engine, DATA)
    municipalities = json.loads((DATA / "municipalities.json").read_text(encoding="utf-8"))
    assert counts["municipality"] == len(municipalities)
    assert counts["olive_area"] == 86
    with engine.connect() as connection:
        for table, expected in counts.items():
            stored = connection.execute(text(f"SELECT count(*) FROM oliveye.{table}")).scalar_one()
            assert stored == expected, table


def test_load_is_idempotent(engine) -> None:  # type: ignore[no-untyped-def]
    first = load_all(engine, DATA)
    second = load_all(engine, DATA)
    assert first == second
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT count(*) FROM oliveye.monthly_index")).scalar_one()
    assert rows == second["monthly_index"]


def test_geometries_are_valid_wgs84_multipolygons(engine) -> None:  # type: ignore[no-untyped-def]
    load_all(engine, DATA)
    with engine.connect() as connection:
        srids = connection.execute(
            text("SELECT DISTINCT ST_SRID(geom), GeometryType(geom) FROM oliveye.olive_area")
        ).all()
    assert srids == [(4326, "MULTIPOLYGON")]


def test_area_in_metres_matches_the_reported_olive_area(engine) -> None:  # type: ignore[no-untyped-def]
    """The dissolved footprint (computed in EPSG:25830) must hold the measured olive hectares.

    The footprint is the union of 6.25 ha cells that are at least 80 % olive, simplified for the
    map, so it is a bit larger than the olive hectares inside it, never wildly different.
    """
    load_all(engine, DATA)
    check = area_check(engine)
    ratio = check["olive_ha"] / check["footprint_ha"]
    assert len(check) == 86
    assert ratio.between(0.8, 1.0).all(), check.loc[~ratio.between(0.8, 1.0)]


def test_campaign_error_view_reproduces_the_published_mape(engine) -> None:  # type: ignore[no-untyped-def]
    load_all(engine, DATA)
    summary = {r["model"]: r for r in json.loads((DATA / "summary.json").read_text("utf-8"))}
    with engine.connect() as connection:
        mape, aforo, rows = connection.execute(
            text(
                "SELECT avg(abs(error_pct)), avg(abs(aforo_error_pct)), count(*) "
                "FROM oliveye.v_campaign_error WHERE like_for_like"
            )
        ).one()
    assert rows == summary["ridge"]["rows"]
    assert round(float(mape), 1) == summary["ridge"]["mape_pct"]
    assert round(float(aforo), 1) == summary["aforo"]["mape_pct"]


def test_database_url_from_postgres_variables() -> None:
    url = database_url({"POSTGRES_PASSWORD": "pw", "POSTGRES_PORT": "5433"})
    assert url == "postgresql+psycopg://oliveye:pw@localhost:5433/oliveye"
    assert database_url({"DATABASE_URL": "postgresql+psycopg://x"}) == "postgresql+psycopg://x"
