"""Tests for campaign features: timing (no leakage) and weighting."""

import pandas as pd
import pytest

from oliveye.models.features import campaign_features, campaign_for_month, province_features


@pytest.mark.parametrize(
    ("month", "expected"),
    [
        ("2021-10", "2022/23"),  # autumn before: feeds the next campaign
        ("2022-04", "2022/23"),  # flowering
        ("2022-08", "2022/23"),  # last month before the aforo
        ("2022-09", None),  # aforo month: excluded
        ("2022-10", "2023/24"),
    ],
)
def test_campaign_for_month_respects_the_aforo_cutoff(month: str, expected: str | None) -> None:
    assert campaign_for_month(pd.Period(month, "M")) == expected


def monthly(values: dict[str, float], municipality: str = "60") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "month": [pd.Period(m, "M") for m in values],
            "province_code": "23",
            "municipality_code": municipality,
            "ndvi_clean": list(values.values()),
            "ndmi_clean": [v / 10 for v in values.values()],
        }
    )


def test_seasonal_means_ignore_months_after_cutoff() -> None:
    data = monthly(
        {"2021-12": 0.46, "2022-01": 0.44, "2022-04": 0.40, "2022-07": 0.27, "2022-09": 0.99}
    )
    row = campaign_features(data).iloc[0]

    assert row["campaign"] == "2022/23"
    assert row["ndvi_winter"] == pytest.approx(0.45)
    assert row["ndvi_spring"] == pytest.approx(0.40)
    assert row["ndvi_summer"] == pytest.approx(0.27)
    assert row["ndmi_summer"] == pytest.approx(0.027)
    assert row["months_valid"] == 4  # September (0.99) is not used
    assert row["ndvi_mean"] == pytest.approx((0.46 + 0.44 + 0.40 + 0.27) / 4)


def test_province_features_weight_by_olive_area() -> None:
    a = campaign_features(monthly({"2022-04": 0.40}, municipality="60"))
    b = campaign_features(monthly({"2022-04": 0.30}, municipality="92"))
    weights = pd.DataFrame(
        {
            "province_code": ["23", "23"],
            "municipality_code": ["60", "92"],
            "olive_hectares": [1000.0, 3000.0],
        }
    )
    result = province_features(pd.concat([a, b]), weights).iloc[0]

    assert result["municipalities"] == 2
    assert result["ndvi_spring"] == pytest.approx((0.40 * 1000 + 0.30 * 3000) / 4000)
