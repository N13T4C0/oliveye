"""Load the published OlivEye data (api/data/) into the PostGIS database of docker-compose.yml.

    docker compose up -d
    uv run --extra db python scripts/load_postgis.py           # reads .env (POSTGRES_*)
    uv run --extra db python scripts/load_postgis.py --check   # also print the area check

Then, for example:

    docker compose exec db psql -U oliveye -d oliveye \\
        -c "SELECT * FROM oliveye.v_campaign_error ORDER BY abs(error_pct) DESC;"
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine

from oliveye.db.load import area_check, database_url, load_all

ROOT = Path(__file__).resolve().parents[1]


def read_dotenv(path: Path) -> None:
    """Minimal .env reader (KEY=value lines); real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "api" / "data")
    parser.add_argument("--check", action="store_true", help="print measured area per municipality")
    args = parser.parse_args()

    read_dotenv(ROOT / ".env")
    engine = create_engine(database_url())
    counts = load_all(engine, args.data_dir)
    for table, rows in counts.items():
        print(f"oliveye.{table:<14} {rows:>7,} rows")
    if args.check:
        check = area_check(engine)
        print(check.round(1).to_string(index=False))
    engine.dispose()


if __name__ == "__main__":
    main()
