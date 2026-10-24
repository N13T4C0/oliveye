"""Tests for leave-one-campaign-out training and evaluation (ADR 0003)."""

import numpy as np
import pandas as pd
import pytest

from oliveye.models.dataset import FEATURES
from oliveye.models.evaluate import interval_bounds, mape, summarise
from oliveye.models.train import (
    baseline_predictions,
    cross_validate_ridge,
    loco_splits,
)


def synthetic_table(noise: float = 0.0, seed: int = 0) -> pd.DataFrame:
    """Two provinces × 8 campaigns whose log production is linear in the features."""
    rng = np.random.default_rng(seed)
    rows = []
    for year in range(2017, 2025):
        campaign = f"{year}/{(year + 1) % 100:02d}"
        for is_granada in (0, 1):
            x = {
                "lag_log_production": rng.normal(12.5, 0.4),
                "hot_days_may": float(rng.integers(0, 8)),
                "ndmi_summer": rng.normal(-0.06, 0.01),
                "ndvi_spring": rng.normal(0.38, 0.03),
            }
            log_y = (
                13.0
                - 0.08 * x["hot_days_may"]
                + 6.0 * x["ndmi_summer"]
                - 1.2 * is_granada
                + rng.normal(0, noise)
            )
            rows.append(
                {
                    "province": "Granada" if is_granada else "Jaén",
                    "campaign": campaign,
                    "is_granada": is_granada,
                    **x,
                    "log_production": log_y,
                    "oil_final_t": float(np.exp(log_y)),
                    "oil_aforo_t": float(np.exp(log_y) * 1.15),  # aforo 15 % too high
                    "mean5_t": float(np.exp(log_y) * 0.9),
                }
            )
    return pd.DataFrame(rows)


def test_loco_holds_out_whole_campaigns() -> None:
    table = synthetic_table()
    splits = list(loco_splits(table))

    assert len(splits) == table["campaign"].nunique()
    for train_idx, test_idx in splits:
        held_out = set(table.loc[test_idx, "campaign"])
        assert len(held_out) == 1
        assert held_out.isdisjoint(set(table.loc[train_idx, "campaign"]))
        assert len(test_idx) == 2  # both provinces of the campaign


def test_ridge_recovers_a_linear_signal_out_of_sample() -> None:
    predictions = cross_validate_ridge(synthetic_table(noise=0.0))

    assert set(predictions["campaign"]) == set(synthetic_table()["campaign"])
    assert mape(predictions["oil_final_t"], predictions["pred_t"]) < 5.0
    assert predictions["alpha"].isin([0.1, 1.0, 10.0]).all()


def test_ridge_never_sees_the_held_out_target() -> None:
    """Corrupting the held-out targets must not change their own predictions."""
    table = synthetic_table(noise=0.05)
    clean = cross_validate_ridge(table).set_index(["campaign", "province"])["pred_t"]

    for campaign in table["campaign"].unique():
        corrupted = table.copy()
        mask = corrupted["campaign"] == campaign
        corrupted.loc[mask, "log_production"] += 5.0
        preds = cross_validate_ridge(corrupted).set_index(["campaign", "province"])["pred_t"]
        assert preds.loc[campaign].to_numpy() == pytest.approx(clean.loc[campaign].to_numpy())


def test_baselines() -> None:
    table = synthetic_table()
    base = baseline_predictions(table)

    row = base.iloc[0]
    assert row["pred_last_t"] == pytest.approx(np.exp(table.iloc[0]["lag_log_production"]))
    assert row["pred_aforo_t"] == pytest.approx(table.iloc[0]["oil_aforo_t"])
    assert row["pred_mean5_t"] == pytest.approx(table.iloc[0]["mean5_t"])


def test_mape_and_intervals() -> None:
    assert mape(pd.Series([100.0, 200.0]), pd.Series([110.0, 180.0])) == pytest.approx(10.0)
    low, high = interval_bounds(pd.Series(np.log([1.2, 0.8, 1.1, 0.9])), coverage=0.8)
    assert low < 1.0 < high


def test_summary_counts_campaigns_closer_than_the_aforo() -> None:
    predictions = cross_validate_ridge(synthetic_table(noise=0.0))
    summary = summarise(predictions, baseline_predictions(synthetic_table(noise=0.0)))

    ridge = summary.set_index("model").loc["ridge"]
    assert ridge["rows"] == 16
    assert ridge["wins_vs_aforo"] == 16  # the synthetic aforo is always 15 % off
    assert {"last_campaign", "mean_5_campaigns", "aforo", "ridge"} <= set(summary["model"])
    assert set(FEATURES) == {"lag_log_production", "hot_days_may", "ndmi_summer", "ndvi_spring"}
