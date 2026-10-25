"""PostGIS loader against a real database (skipped unless OLIVEYE_TEST_DATABASE_URL is set).

The tests drop and recreate the `oliveye` schema, so they refuse to run unless the database name
ends in `_test` (or under CI). Locally, with `docker compose up -d` running:

    docker compose exec db createdb -U oliveye oliveye_test
    export OLIVEYE_TEST_DATABASE_URL=postgresql+psycopg://oliveye:<pw>@localhost:5432/oliveye_test
    uv run --extra db pytest tests/test_db.py

CI runs them against a `postgis/postgis:17-3.5` service container.
"""

import json
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("geoalchemy2", reason="install the 'db' extra to run PostGIS tests")
URL = os.environ.get("OLIVEYE_TEST_DATABASE_URL")
if not URL:
    pytest.skip("OLIVEYE_TEST_DATABASE_URL not set", allow_module_level=True)

from oliveye_api import campaign_errors  # noqa: E402
from sqlalchemy import Engine, create_engine, make_url, text  # noqa: E402

from oliveye.db.load import area_check, load_all  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "api" / "data"
MEASURED = len(json.loads((DATA / "map.geojson").read_text(encoding="utf-8"))["features"])


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    url = make_url(URL)
    if not (url.database or "").endswith("_test") and not os.environ.get("CI"):
        pytest.fail(f"Refusing to drop schema 'oliveye' in {url.database!r}: use a *_test database")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS oliveye CASCADE"))
    yield engine
    engine.dispose()


def _counts(engine: Engine) -> dict[str, int]:
    tables = ("municipality", "olive_area", "monthly_index", "production")
    with engine.connect() as connection:
        return {
            t: connection.execute(text(f"SELECT count(*) FROM oliveye.{t}")).scalar_one()
            for t in tables
        }


def test_load_counts_match_the_published_files(engine: Engine) -> None:
    counts = load_all(engine, DATA)
    municipalities = json.loads((DATA / "municipalities.json").read_text(encoding="utf-8"))
    assert counts["municipality"] == len(municipalities)
    assert counts["olive_area"] == MEASURED
    assert _counts(engine) == counts


def test_load_is_idempotent(engine: Engine) -> None:
    first = load_all(engine, DATA)
    second = load_all(engine, DATA)
    assert first == second == _counts(engine)


def test_failed_load_leaves_previous_data_untouched(engine: Engine, tmp_path: Path) -> None:
    load_all(engine, DATA)
    before = _counts(engine)
    broken = tmp_path / "data"
    shutil.copytree(DATA, broken)
    collection = json.loads((broken / "map.geojson").read_text(encoding="utf-8"))
    # A self-intersecting "bowtie" polygon: ST_IsValid is false, so the load must roll back.
    collection["features"][0]["geometry"] = {
        "type": "MultiPolygon",
        "coordinates": [[[[-3.8, 37.7], [-3.7, 37.8], [-3.7, 37.7], [-3.8, 37.8], [-3.8, 37.7]]]],
    }
    (broken / "map.geojson").write_text(json.dumps(collection), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid geometries"):
        load_all(engine, broken)
    assert _counts(engine) == before


def test_geometries_are_valid_wgs84_multipolygons(engine: Engine) -> None:
    load_all(engine, DATA)
    with engine.connect() as connection:
        srids = connection.execute(
            text("SELECT DISTINCT ST_SRID(geom), GeometryType(geom) FROM oliveye.olive_area")
        ).all()
    assert srids == [(4326, "MULTIPOLYGON")]


def test_area_in_metres_matches_the_reported_olive_area(engine: Engine) -> None:
    """The dissolved footprint (computed in EPSG:25830) must hold the measured olive hectares.

    The footprint is the union of 6.25 ha cells that are at least 80 % olive, simplified for the
    map, so it is a bit larger than the olive hectares inside it (89-97 % on 2026-10-25).
    """
    load_all(engine, DATA)
    check = area_check(engine)
    ratio = check["olive_ha"] / check["footprint_ha"]
    assert len(check) == MEASURED
    assert ratio.between(0.8, 1.0).all(), check.loc[~ratio.between(0.8, 1.0)]


def test_campaign_error_view_reproduces_the_published_mape(engine: Engine) -> None:
    load_all(engine, DATA)
    summary = {r["model"]: r for r in json.loads((DATA / "summary.json").read_text("utf-8"))}
    with engine.connect() as connection:
        mape, aforo, rows, closer = connection.execute(
            text(
                "SELECT avg(abs(error_pct)), avg(abs(aforo_error_pct)), count(*), "
                "count(*) FILTER (WHERE closer = 'oliveye') "
                "FROM oliveye.v_campaign_error WHERE like_for_like"
            )
        ).one()
    assert rows == summary["ridge"]["rows"]
    assert round(float(mape), 1) == summary["ridge"]["mape_pct"]
    assert round(float(aforo), 1) == summary["aforo"]["mape_pct"]
    production = json.loads((DATA / "production.json").read_text("utf-8"))
    assert closer == sum(row["closer"] == "oliveye" for row in campaign_errors(production))


def test_production_joins_municipalities_by_province_code(engine: Engine) -> None:
    load_all(engine, DATA)
    with engine.connect() as connection:
        orphans = connection.execute(
            text(
                "SELECT count(*) FROM oliveye.production p WHERE NOT EXISTS "
                "(SELECT 1 FROM oliveye.municipality m WHERE m.province_code = p.province_code)"
            )
        ).scalar_one()
    assert orphans == 0
