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


def test_previous_campaign() -> None:
    from oliveye.pipeline.production import previous_campaign

    assert previous_campaign("2024/25") == "2023/24"
    assert previous_campaign("2000/01") == "1999/00"


def test_final_series_reindexes_and_prefers_first_source() -> None:
    import pandas as pd

    from oliveye.pipeline.production import final_production_series

    pdf = pd.DataFrame(
        {
            "campaign": ["2024/25"],
            "province": ["Jaén"],
            "oil_aforo_t": [445_000.0],
            "oil_var_prev_pct": [116.1],
        }
    )
    press = pd.DataFrame(
        {
            "campaign": ["2024/25", "2016/17", "2020/21"],
            "province": ["Jaén", "Jaén", "Jaén"],
            "oil_aforo_t": [1.0, 542_000.0, 670_000.0],
            "oil_var_prev_pct": [0.0, 2.5, None],  # 2020/21 has no variation: unusable
        }
    )
    series = final_production_series(pdf, press)

    assert list(series["campaign"]) == ["2015/16", "2023/24"]
    assert series.set_index("campaign").loc["2023/24", "oil_final_t_derived"] == 205_900
    assert series.set_index("campaign").loc["2015/16", "oil_final_t_derived"] == 528_800


def test_reported_values_win_over_derived() -> None:
    import pandas as pd

    from oliveye.pipeline.production import target_series

    derived = pd.DataFrame(
        {
            "campaign": ["2018/19", "2020/21"],
            "province": ["Jaén", "Jaén"],
            "oil_final_t_derived": [665_200.0, 524_000.0],
            "source_campaign": ["2019/20", "2021/22"],
        }
    )
    reported = pd.DataFrame(
        {
            "campaign": ["2018/19"],
            "province": ["Jaén"],
            "oil_final_t": [667_855.0],
            "method": ["reported"],
        }
    )
    series = target_series(derived, reported).set_index("campaign")

    assert series.loc["2018/19", "oil_final_t"] == 667_855
    assert series.loc["2018/19", "method"] == "reported"
    assert series.loc["2020/21", "method"] == "derived_from_aforo"
