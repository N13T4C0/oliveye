"""Tests for the province × campaign table (ADR 0003: features, lag, timing)."""

import numpy as np
import pandas as pd
import pytest

from oliveye.models.dataset import (
    FEATURES,
    climate_features,
    five_campaign_mean,
    province_table,
)


def daily_weather(cell: str, year: int, may_tmax: list[float]) -> pd.DataFrame:
    """May of `year` with the given maxima, plus a scorching September that must be ignored."""
    may = pd.DataFrame(
        {
            "cell_id": cell,
            "date": pd.date_range(f"{year}-05-01", periods=len(may_tmax), freq="D"),
            "tmax_c": may_tmax,
        }
    )
    september = pd.DataFrame(
        {"cell_id": cell, "date": pd.date_range(f"{year}-09-01", periods=5), "tmax_c": 45.0}
    )
    return pd.concat([may, september], ignore_index=True)


def test_hot_days_count_may_of_the_campaign_start_year_only() -> None:
    weather = daily_weather("c1", 2022, [30.0, 33.0, 35.0, 31.9, 32.1])
    points = pd.DataFrame({"id": ["23-60"], "cell_id": ["c1"]})

    result = climate_features(weather, points)

    row = result.set_index("campaign").loc["2022/23"]
    assert row["province_code"] == "23" and row["municipality_code"] == "60"
    assert row["hot_days_may"] == 3  # 33.0, 35.0, 32.1 (> 32 °C); September is ignored


def test_five_campaign_mean_uses_only_past_campaigns() -> None:
    target = pd.DataFrame(
        {
            "province": "Jaén",
            "campaign": ["2017/18", "2018/19", "2019/20", "2020/21"],
            "oil_final_t": [100.0, 200.0, 300.0, 400.0],
        }
    )
    means = five_campaign_mean(target).set_index("campaign")["mean5_t"]

    assert np.isnan(means.loc["2017/18"])  # no past campaign
    assert means.loc["2020/21"] == pytest.approx(200.0)  # mean of 100, 200, 300 (not 400)


def make_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    municipal = pd.DataFrame(
        {
            "province_code": ["23", "23", "23", "23"],
            "municipality_code": ["60", "92", "60", "92"],
            "campaign": ["2021/22", "2021/22", "2022/23", "2022/23"],
            "ndvi_spring": [0.40, 0.30, 0.38, 0.28],
            "ndmi_summer": [-0.05, -0.07, -0.06, -0.08],
        }
    )
    climate = pd.DataFrame(
        {
            "province_code": ["23", "23", "23", "23"],
            "municipality_code": ["60", "92", "60", "92"],
            "campaign": ["2021/22", "2021/22", "2022/23", "2022/23"],
            "hot_days_may": [1, 3, 5, 5],
        }
    )
    weights = pd.DataFrame(
        {
            "province_code": ["23", "23"],
            "municipality_code": ["60", "92"],
            "olive_hectares": [1000.0, 3000.0],
        }
    )
    target = pd.DataFrame(
        {
            "province": "Jaén",
            "campaign": ["2020/21", "2021/22", "2022/23"],
            "oil_final_t": [524_000.0, 500_000.0, 179_900.0],
            "method": "derived_from_aforo",
        }
    )
    aforo = pd.DataFrame(
        {
            "province": "Jaén",
            "campaign": ["2021/22", "2022/23"],
            "oil_aforo_t": [480_000.0, 200_000.0],
        }
    )
    return municipal, climate, weights, target, aforo


def test_province_table_weights_lags_and_logs() -> None:
    table = province_table(*make_inputs()).set_index("campaign")

    assert list(table.index) == ["2021/22", "2022/23"]
    jaen = table.loc["2022/23"]
    assert jaen["ndvi_spring"] == pytest.approx((0.38 * 1000 + 0.28 * 3000) / 4000)
    assert jaen["hot_days_may"] == pytest.approx(5.0)
    assert jaen["lag_log_production"] == pytest.approx(np.log(500_000.0))  # 2021/22
    assert jaen["log_production"] == pytest.approx(np.log(179_900.0))
    assert jaen["is_granada"] == 0
    assert jaen["oil_aforo_t"] == 200_000.0
    assert set(FEATURES) <= set(table.columns)


def test_rows_without_the_previous_campaign_are_dropped() -> None:
    municipal, climate, weights, target, aforo = make_inputs()
    target = target[target["campaign"] != "2020/21"]  # 2021/22 loses its lag

    table = province_table(municipal, climate, weights, target, aforo)

    assert list(table["campaign"]) == ["2022/23"]
