"""Offline tests for the aforo table parser (synthetic rows, no PDF download)."""

import pytest

from oliveye.pipeline.production import (
    PROVINCES,
    normalise_campaign,
    parse_province_table,
    parse_spanish_number,
)

HEADER = [
    "PROVINCIA",
    "Aforo aceituna de\nalmazara (t)",
    "Aforo aceite de oliva (t)",
    "Variación aceite\n(media 5 últimas\ncampañas)",
    "Variación aceite\n(campaña anterior)",
]


def table(header: list[str]) -> list[list[str | None]]:
    rows: list[list[str | None]] = [list(header)]
    for name in PROVINCES:
        label = "ANDALUCÍA" if name == "Andalucía" else name
        rows.append([label, "2.100.000", "445.000", "22,6 %", "116,1 %"])
    return rows


def test_parse_spanish_numbers() -> None:
    assert parse_spanish_number("1.021.000") == 1_021_000
    assert parse_spanish_number("-43,5 %") == -43.5


@pytest.mark.parametrize(
    "text", ["aforo_2024_25", "Estimacion_ACEITE_MESA_2024_2025", "campaña 2024/25"]
)
def test_normalise_campaign(text: str) -> None:
    assert normalise_campaign(text) == "2024/25"


def test_normalise_campaign_rejects_non_consecutive_years() -> None:
    with pytest.raises(ValueError):
        normalise_campaign("aforo_2024_27")


def test_parse_table_uses_headers_and_derives_previous_campaign() -> None:
    df = parse_province_table(table(HEADER), "2024/25")
    jaen = df.set_index("province").loc["Jaén"]

    assert len(df) == len(PROVINCES)
    assert jaen["province_code"] == "23"
    assert jaen["oil_aforo_t"] == 445_000
    assert jaen["oil_var_prev_pct"] == pytest.approx(116.1)
    assert jaen["oil_var_5y_pct"] == pytest.approx(22.6)
    assert jaen["oil_prev_final_t_derived"] == 205_900  # 445,000 / 2.161, rounded to 100 t
    assert "Andalucía" in set(df["province"])


def test_parse_table_does_not_depend_on_column_order() -> None:
    swapped = [HEADER[0], HEADER[1], HEADER[2], HEADER[4], HEADER[3]]
    df = parse_province_table(table(swapped), "2024/25")
    # With swapped headers the same cell values are read as the other variation.
    assert df.set_index("province").loc["Jaén", "oil_var_prev_pct"] == pytest.approx(22.6)
