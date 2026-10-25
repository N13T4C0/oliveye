"""Features per municipality/province and campaign from the monthly satellite indices.

Timing (the most important modelling decision, see the oliveye-auditor leakage checks):

* Campaign "2022/23" is the harvest from October 2022 to September 2023. Its fruit is formed in
  the **previous** months: flowering in April–May 2022, fruit set and oil accumulation in summer
  and early autumn 2022.
* The official aforo for "2022/23" is published in mid/late **October 2022** and also uses field
  fruit counts. Features for campaign Y/Y+1 use only the months **October Y-1 to August Y** (the
  cut-off is a parameter), so the model always knows less than the aforo, never more.

Example: features for "2022/23" come from Oct 2021–Aug 2022; the drought of spring 2022 shows up
as a low `ndvi_spring` and a very negative `ndmi_summer` for that campaign.
"""

from __future__ import annotations

import pandas as pd

# Season windows by calendar month (all inside Oct Y-1 .. Aug Y).
SEASONS: dict[str, tuple[int, ...]] = {
    "winter": (12, 1, 2),
    "spring": (3, 4, 5),
    "summer": (6, 7, 8),
}
FEATURE_COLUMNS = [
    "ndvi_mean",
    "ndvi_winter",
    "ndvi_spring",
    "ndvi_summer",
    "ndmi_spring",
    "ndmi_summer",
    "months_valid",
]


def campaign_for_month(month: pd.Period, cutoff_month: int = 8) -> str | None:
    """Campaign whose features this month feeds, or None if it falls after the cut-off.

    Months October..December of year Y-1 and January..`cutoff_month` of year Y feed campaign
    "Y/Y+1". Months after the cut-off (e.g. September) feed nothing: they come after the aforo.
    """
    if month.month >= 10:
        start = month.year + 1
    elif month.month <= cutoff_month:
        start = month.year
    else:
        return None
    return f"{start}/{(start + 1) % 100:02d}"


def campaign_features(
    monthly: pd.DataFrame,
    *,
    id_columns: tuple[str, ...] = ("province_code", "municipality_code"),
    ndvi: str = "ndvi_clean",
    ndmi: str = "ndmi_clean",
    cutoff_month: int = 8,
) -> pd.DataFrame:
    """One row per area and campaign with seasonal NDVI/NDMI means (outliers already removed).

    Args:
        monthly: output of `clean_monthly_indices` (columns `month` as Period[M], the id
            columns, `ndvi_clean`, `ndmi_clean`).
        cutoff_month: last calendar month used for a campaign (8 = August, before the aforo).
    """
    data = monthly.copy()
    data["campaign"] = [campaign_for_month(m, cutoff_month) for m in data["month"]]
    data = data.dropna(subset=["campaign"])
    data["calendar_month"] = [m.month for m in data["month"]]

    keys = [*id_columns, "campaign"]
    grouped = data.groupby(keys)
    features = pd.DataFrame(
        {
            "ndvi_mean": grouped[ndvi].mean(),
            "months_valid": grouped[ndvi].count(),
        }
    )
    for season, months in SEASONS.items():
        in_season = data[data["calendar_month"].isin(months)].groupby(keys)
        features[f"ndvi_{season}"] = in_season[ndvi].mean()
        if season in ("spring", "summer"):
            features[f"ndmi_{season}"] = in_season[ndmi].mean()
    return features[FEATURE_COLUMNS].reset_index()


def province_features(
    municipal: pd.DataFrame,
    weights: pd.DataFrame,
    *,
    weight_column: str = "olive_hectares",
) -> pd.DataFrame:
    """Olive-area-weighted mean of municipal features per province and campaign.

    `weights` has `province_code`, `municipality_code` and the municipality's total olive area
    (from the SIGPAC ranking), so a large olive municipality counts more than a small one, even
    if fewer of its cells were pure enough to be sampled. Missing features are skipped (the
    weights of the remaining municipalities are renormalised).
    """
    merged = municipal.merge(
        weights[["province_code", "municipality_code", weight_column]],
        on=["province_code", "municipality_code"],
        how="inner",
    )
    value_columns = [c for c in FEATURE_COLUMNS if c != "months_valid"]
    rows = []
    for (province, campaign), group in merged.groupby(["province_code", "campaign"]):
        row: dict[str, object] = {
            "province_code": province,
            "campaign": campaign,
            "municipalities": len(group),
        }
        for column in value_columns:
            valid = group[group[column].notna()]
            total = valid[weight_column].sum()
            row[column] = (valid[column] * valid[weight_column]).sum() / total if total else None
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["province_code", "campaign"]).reset_index(drop=True)
