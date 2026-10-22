"""Tests for oliveye.pipeline.sigpac using a tiny local GeoParquet that mimics the real schema."""

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from oliveye.pipeline.sigpac import (
    fetch_and_cache_municipality,
    fetch_municipality_parcels,
    rank_municipalities_by_olive_area,
)


@pytest.fixture
def fake_sigpac(tmp_path: Path) -> str:
    """Six parcels in two municipalities of province 23, plus one parcel in province 18."""
    gdf = gpd.GeoDataFrame(
        {
            "id": ["a", "b", "c", "d", "e", "f", "g"],
            "crop:code": ["OV", "OV", "TA", "PS", "OV", "OV", "OV"],
            "crop:name": [
                "OLIVAR",
                "OLIVAR",
                "TIERRAS ARABLES",
                "PASTIZAL",
                "OLIVAR",
                "OLIVAR",
                "OLIVAR",
            ],
            "admin_province_code": [23, 23, 23, 23, 23, 23, 18],
            "admin_municipality_code": [60, 60, 60, 60, 92, 92, 60],
            "metrics:area": [20_000.0, 30_000.0, 10_000.0, 5_000.0, 10_000.0, 10_000.0, 99_000.0],
        },
        geometry=[box(i, 0, i + 1, 1) for i in range(7)],
        crs="EPSG:25830",
    )
    path = tmp_path / "sigpac.parquet"
    gdf.to_parquet(path)
    return str(path)


def test_rank_orders_by_olive_area_within_province(fake_sigpac: str) -> None:
    ranking = rank_municipalities_by_olive_area("23", source=fake_sigpac)

    assert [r.municipality_code for r in ranking] == ["60", "92"]
    assert ranking[0].olive_hectares == pytest.approx(5.0)  # 2 ha + 3 ha, TA/PS excluded
    assert ranking[0].parcels == 2


def test_fetch_keeps_only_requested_land_uses(fake_sigpac: str) -> None:
    parcels = fetch_municipality_parcels("23", "60", source=fake_sigpac)

    assert sorted(parcels["parcel_id"]) == ["a", "b", "c"]  # pasture and other province excluded
    assert set(parcels["land_use_code"]) == {"OV", "TA"}
    assert parcels.crs.to_epsg() == 25830
    assert parcels.geometry.is_valid.all()


def test_cache_is_reused(fake_sigpac: str, tmp_path: Path) -> None:
    out = tmp_path / "out"
    first = fetch_and_cache_municipality("23", "60", out, source=fake_sigpac)
    mtime = first.stat().st_mtime_ns

    second = fetch_and_cache_municipality("23", "60", out, source=fake_sigpac)

    assert first == second
    assert second.stat().st_mtime_ns == mtime  # not rewritten


def test_unknown_municipality_raises(fake_sigpac: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No parcels found"):
        fetch_and_cache_municipality("23", "999", tmp_path, source=fake_sigpac)
