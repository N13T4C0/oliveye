from pathlib import Path

import pytest

from oliveye.pipeline.prices import price_payload

SOURCES = Path(__file__).resolve().parents[1] / "docs" / "sources"


def test_latest_week_and_range(tmp_path: Path) -> None:
    csv = tmp_path / "prices.csv"
    csv.write_text(
        "week_start,week_end,category,eur_per_kg,source,source_url,note\n"
        "2026-10-06,2026-10-12,virgen_extra,3.40,Poolred,https://x,\n"
        "2026-10-13,2026-10-19,virgen_extra,3.16,Poolred,https://x,\n"
        "2026-10-13,2026-10-19,lampante,2.88,Poolred,https://x,\n",
        encoding="utf-8",
    )
    payload = price_payload(csv)
    assert payload["week_end"] == "2026-10-19"
    assert payload["low_eur_per_kg"] == 2.88
    assert payload["high_eur_per_kg"] == 3.16


def test_unknown_category_is_rejected(tmp_path: Path) -> None:
    csv = tmp_path / "prices.csv"
    csv.write_text(
        "week_start,week_end,category,eur_per_kg,source,source_url,note\n"
        "2026-10-13,2026-10-19,orujo,1.0,Poolred,https://x,\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="orujo"):
        price_payload(csv)


def test_curated_table_is_valid() -> None:
    payload = price_payload(SOURCES / "oil_prices.csv")
    assert 0 < payload["low_eur_per_kg"] <= payload["high_eur_per_kg"] < 20
