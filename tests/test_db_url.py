"""Connection URL for the PostGIS loader (no database needed)."""

import pytest

pytest.importorskip("sqlalchemy", reason="install the 'db' extra")

from oliveye.db.load import database_url  # noqa: E402


def test_database_url_from_postgres_variables() -> None:
    url = database_url({"POSTGRES_PASSWORD": "pw", "POSTGRES_PORT": "5433"})
    assert url == "postgresql+psycopg://oliveye:pw@localhost:5433/oliveye"


def test_special_characters_in_the_password_are_escaped() -> None:
    url = database_url({"POSTGRES_PASSWORD": "p@ss:w/rd#1"})
    assert url == "postgresql+psycopg://oliveye:p%40ss%3Aw%2Frd%231@localhost:5432/oliveye"


def test_database_url_wins() -> None:
    assert database_url({"DATABASE_URL": "postgresql+psycopg://x"}) == "postgresql+psycopg://x"


def test_missing_password_is_an_error() -> None:
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        database_url({})
