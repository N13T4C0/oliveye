"""Province × campaign modelling table (ADR 0003).

One row per province and campaign with:

* the four features fixed a priori: lagged log production (alternate bearing), May days above
  32 °C (heat at flowering), summer NDMI (water stress) and spring NDVI (vigour);
* `is_granada` (province indicator), the target `log_production`, and the comparison columns
  `oil_aforo_t` (official forecast) and `mean5_t` (mean of the previous five campaigns).

Municipal features are aggregated to the province as means weighted by SIGPAC olive hectares.
All inputs respect the August cut-off of `oliveye.models.features`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from oliveye.pipeline.production import PROVINCE_CODES

FEATURES: list[str] = ["lag_log_production", "hot_days_may", "ndmi_summer", "ndvi_spring"]
HOT_DAY_C = 32.0
_KEYS = ["province_code", "municipality_code"]
_CODE_TO_PROVINCE = {code: name for name, code in PROVINCE_CODES.items()}


def climate_features(
    daily: pd.DataFrame, points: pd.DataFrame, *, hot_day_c: float = HOT_DAY_C
) -> pd.DataFrame:
    """May days above `hot_day_c` per municipality and campaign.

    May of year Y feeds campaign "Y/Y+1" (flowering before that harvest, before the aforo).

    Args:
        daily: `cell_id`, `date`, `tmax_c` (Open-Meteo ERA5 output).
        points: `id` ("<province>-<municipality>") and its `cell_id`.
    """
    may = daily[pd.to_datetime(daily["date"]).dt.month == 5].copy()
    may["year"] = pd.to_datetime(may["date"]).dt.year
    hot = (
        may.assign(hot=may["tmax_c"] > hot_day_c)
        .groupby(["cell_id", "year"], as_index=False)["hot"]
        .sum()
    )
    codes = points["id"].astype(str).str.split("-", n=1, expand=True)
    mapping = pd.DataFrame(
        {"province_code": codes[0], "municipality_code": codes[1], "cell_id": points["cell_id"]}
    )
    merged = mapping.merge(hot, on="cell_id", how="inner")
    merged["campaign"] = [f"{y}/{(y + 1) % 100:02d}" for y in merged["year"]]
    merged["hot_days_may"] = merged["hot"].astype(float)
    return merged[[*_KEYS, "campaign", "hot_days_may"]].reset_index(drop=True)


def five_campaign_mean(target: pd.DataFrame) -> pd.DataFrame:
    """Mean production of up to five previous campaigns per province (past only)."""
    ordered = target.sort_values(["province", "campaign"]).copy()
    ordered["mean5_t"] = ordered.groupby("province")["oil_final_t"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=1).mean()
    )
    return ordered[["province", "campaign", "mean5_t"]]


def _weighted(group: pd.DataFrame, column: str, weight: str) -> float:
    valid = group[group[column].notna()]
    total = float(valid[weight].sum())
    return float((valid[column] * valid[weight]).sum() / total) if total else float("nan")


def province_table(
    municipal: pd.DataFrame,
    climate: pd.DataFrame,
    weights: pd.DataFrame,
    target: pd.DataFrame,
    aforo: pd.DataFrame,
    *,
    weight_column: str = "olive_hectares",
) -> pd.DataFrame:
    """Assemble the modelling table; rows missing the target, its lag or a feature are dropped.

    Args:
        municipal: `campaign_features` output (needs `ndvi_spring`, `ndmi_summer`).
        climate: `climate_features` output.
        weights: SIGPAC olive hectares per municipality.
        target: `target_series` output (`province`, `campaign`, `oil_final_t`).
        aforo: official forecast (`province`, `campaign`, `oil_aforo_t`).
    """
    features = municipal[[*_KEYS, "campaign", "ndvi_spring", "ndmi_summer"]].merge(
        climate, on=[*_KEYS, "campaign"], how="outer"
    )
    features = features.merge(weights[[*_KEYS, weight_column]], on=_KEYS, how="inner")
    rows = []
    for (province_code, campaign), group in features.groupby(["province_code", "campaign"]):
        rows.append(
            {
                "province": _CODE_TO_PROVINCE.get(str(province_code), str(province_code)),
                "campaign": campaign,
                **{c: _weighted(group, c, weight_column) for c in FEATURES[1:]},
            }
        )
    table = pd.DataFrame(rows)

    production = target[["province", "campaign", "oil_final_t"]].copy()
    lag = production.assign(campaign=production["campaign"].map(next_campaign)).rename(
        columns={"oil_final_t": "lag_t"}
    )
    table = table.merge(production, on=["province", "campaign"], how="inner")
    table = table.merge(lag, on=["province", "campaign"], how="left")
    table = table.merge(five_campaign_mean(target), on=["province", "campaign"], how="left")
    table = table.merge(
        aforo[["province", "campaign", "oil_aforo_t"]], on=["province", "campaign"], how="left"
    )

    table["lag_log_production"] = np.log(table["lag_t"])
    table["log_production"] = np.log(table["oil_final_t"])
    table["is_granada"] = (table["province"] == "Granada").astype(int)
    table = table.dropna(subset=[*FEATURES, "log_production"])
    columns = [
        "province",
        "campaign",
        "is_granada",
        *FEATURES,
        "log_production",
        "oil_final_t",
        "oil_aforo_t",
        "mean5_t",
    ]
    return table[columns].sort_values(["province", "campaign"]).reset_index(drop=True)


def next_campaign(campaign: str) -> str:
    """'2021/22' -> '2022/23': the campaign for which this production is the lag."""
    start = int(campaign[:4]) + 1
    return f"{start}/{(start + 1) % 100:02d}"
