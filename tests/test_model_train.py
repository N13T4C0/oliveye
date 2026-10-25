"""Tests for leave-one-campaign-out training and evaluation (ADR 0003)."""

import numpy as np
import pandas as pd
import pytest

from oliveye.models.dataset import FEATURES, next_campaign
from oliveye.models.evaluate import interval_bounds, mape, summarise
from oliveye.models.train import (
    ALPHAS,
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
    grid = np.array(ALPHAS)
    assert all(np.isclose(grid, a).any() for a in predictions["alpha"])


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
    assert ridge["campaign_wins_vs_aforo"] == 8
    assert ridge["p_vs_aforo"] == pytest.approx(2 / 256, abs=1e-3)  # 8 of 8 campaigns better
    assert summary["rows"].nunique() == 1  # like-for-like: every model on the same rows
    assert {"last_campaign", "mean_5_campaigns", "province_mean", "aforo", "ridge"} <= set(
        summary["model"]
    )
    assert set(FEATURES) == {"lag_log_production", "hot_days_may", "ndmi_summer", "ndvi_spring"}


# --- Amendments after the statistician review (ADR 0003, 2026-10-25) -------------------------


def test_loco_also_drops_the_next_campaign_from_training() -> None:
    """Campaign t+1's lag feature is t's real production: it must not train a model for t."""
    table = synthetic_table()
    for train_idx, test_idx in loco_splits(table):
        held_out = table.loc[test_idx, "campaign"].iloc[0]
        assert next_campaign(held_out) not in set(table.loc[train_idx, "campaign"])


def test_held_out_production_never_reaches_its_prediction_through_the_lag() -> None:
    """Corrupt the *production* of a campaign (which also feeds t+1's lag) end to end."""
    from oliveye.models.dataset import province_table

    rng = np.random.default_rng(1)
    years = range(2016, 2025)
    campaigns = [f"{y}/{(y + 1) % 100:02d}" for y in years]
    municipal = pd.DataFrame(
        {
            "province_code": "23",
            "municipality_code": "60",
            "campaign": campaigns,
            "ndvi_spring": rng.normal(0.38, 0.03, len(campaigns)),
            "ndmi_summer": rng.normal(-0.06, 0.01, len(campaigns)),
        }
    )
    climate = municipal[["province_code", "municipality_code", "campaign"]].assign(
        hot_days_may=rng.integers(0, 8, len(campaigns)).astype(float)
    )
    weights = pd.DataFrame(
        {"province_code": ["23"], "municipality_code": ["60"], "olive_hectares": [1.0]}
    )
    target = pd.DataFrame(
        {
            "province": "Jaén",
            "campaign": campaigns,
            "oil_final_t": rng.uniform(2e5, 6e5, len(campaigns)),
            "method": "x",
        }
    )
    aforo = target[["province", "campaign"]].assign(oil_aforo_t=4e5)

    def predict_all(t: pd.DataFrame) -> pd.Series:
        table = province_table(municipal, climate, weights, t, aforo)
        return cross_validate_ridge(table).set_index("campaign")["pred_t"]

    clean = predict_all(target)
    for campaign in clean.index:
        corrupted = target.copy()
        corrupted.loc[corrupted["campaign"] == campaign, "oil_final_t"] *= 3
        assert predict_all(corrupted).loc[campaign] == pytest.approx(clean.loc[campaign])


def test_forward_splits_train_only_on_the_past() -> None:
    from oliveye.models.train import forward_splits

    table = synthetic_table()
    splits = list(forward_splits(table, min_train_campaigns=3))
    assert splits, "expected at least one forward split"
    for train_idx, test_idx in splits:
        held_out = table.loc[test_idx, "campaign"].iloc[0]
        assert (table.loc[train_idx, "campaign"] < held_out).all()
        assert table.loc[train_idx, "campaign"].nunique() >= 3


def test_province_centering_uses_training_means_only() -> None:
    from oliveye.models.train import ProvinceCentering

    train = pd.DataFrame({"x": [1.0, 3.0, 10.0, 14.0], "is_granada": [0, 0, 1, 1]})
    test = pd.DataFrame({"x": [2.0, 20.0], "is_granada": [0, 1]})
    centred = ProvinceCentering().fit(train).transform(test)

    assert centred["x"].tolist() == [0.0, 8.0]  # 2 − mean(1, 3); 20 − mean(10, 14)
    assert centred["is_granada"].tolist() == [0, 1]  # the indicator keeps the level


def test_clipper_limits_test_features_to_the_training_range() -> None:
    from oliveye.models.train import RangeClipper

    clipper = RangeClipper().fit(pd.DataFrame({"x": [0.0, 1.0]}))
    assert clipper.transform(pd.DataFrame({"x": [-5.0, 0.5, 9.0]}))["x"].tolist() == [0.0, 0.5, 1.0]


def test_sign_flip_test_matches_the_exact_value() -> None:
    from oliveye.models.evaluate import sign_flip_p_value

    # 7 campaigns better than the aforo and 1 worse, equal magnitudes → p = 18/256.
    differences = pd.Series([-1.0] * 7 + [1.0])
    assert sign_flip_p_value(differences) == pytest.approx(18 / 256)


def test_conformal_interval_uses_the_ceil_rank() -> None:
    from oliveye.models.evaluate import conformal_half_width

    residuals = pd.Series(np.log([1.1, 0.9, 1.3, 0.7, 1.05]))  # |log| sorted ≈ .05 .10 .11 .26 .36
    q = conformal_half_width(residuals, coverage=0.8)  # rank ceil(6 × 0.8) = 5 → the largest
    assert q == pytest.approx(abs(np.log(0.7)))


def test_infinite_shrinkage_falls_back_to_the_province_mean() -> None:
    """The province level is never penalised: alpha → ∞ must give the province-mean baseline."""
    table = synthetic_table(noise=0.1)
    ridge = cross_validate_ridge(table, alphas=(1e12,))
    base = baseline_predictions(table)
    merged = ridge.merge(base, on=["campaign", "province"])
    assert merged["pred_t"].to_numpy() == pytest.approx(merged["pred_province_mean_t"].to_numpy())


def test_province_level_survives_strong_shrinkage() -> None:
    """With a 3x level gap between provinces, heavy shrinkage must still keep that gap."""
    table = synthetic_table(noise=0.0)
    ridge = cross_validate_ridge(table, alphas=(1e3,)).groupby("province")["pred_log"].mean()
    truth = table.groupby("province")["log_production"].mean()
    assert ridge["Jaén"] - ridge["Granada"] == pytest.approx(
        truth["Jaén"] - truth["Granada"], abs=0.2
    )


def test_choose_alpha_survives_too_few_inner_folds() -> None:
    from oliveye.models.train import choose_alpha, forward_splits

    table = synthetic_table().query("campaign <= '2021/22'")  # 5 campaigns, 1 forward fold
    alpha = choose_alpha(table, ["hot_days_may", "is_granada"], ALPHAS, splitter=forward_splits)
    assert alpha == max(ALPHAS)


def test_unseen_province_is_an_error_not_a_pooled_guess() -> None:
    from oliveye.models.train import ProvinceAnomalyRidge

    train = synthetic_table().query("is_granada == 0")
    model = ProvinceAnomalyRidge(alpha=1.0).fit(
        train[["hot_days_may", "is_granada"]], train["log_production"]
    )
    with pytest.raises(ValueError, match="province"):
        model.predict(pd.DataFrame({"hot_days_may": [1.0], "is_granada": [1]}))


def test_splits_never_score_a_province_without_training_rows() -> None:
    from oliveye.models.train import forward_splits

    table = synthetic_table()
    # Granada observed only in the first two campaigns (like a province with short history).
    table = table[(table["is_granada"] == 0) | (table["campaign"] <= "2018/19")]
    for splitter in (loco_splits, lambda t: forward_splits(t, min_train_campaigns=1)):
        for train_idx, test_idx in splitter(table):
            assert len(test_idx) > 0
            assert set(table.loc[test_idx, "province"]) <= set(table.loc[train_idx, "province"])
    assert len(cross_validate_ridge(table)) > 0  # runs end to end instead of raising


def test_table_says_how_each_target_value_was_obtained() -> None:
    """Derived (from aforo variations) vs reported targets must stay visible downstream."""
    from oliveye.models.dataset import province_table

    campaigns = [f"{y}/{(y + 1) % 100:02d}" for y in range(2016, 2022)]
    municipal = pd.DataFrame(
        {
            "province_code": "23",
            "municipality_code": "60",
            "campaign": campaigns,
            "ndvi_spring": 0.4,
            "ndmi_summer": -0.06,
        }
    )
    climate = municipal[["province_code", "municipality_code", "campaign"]].assign(hot_days_may=2.0)
    weights = pd.DataFrame(
        {"province_code": ["23"], "municipality_code": ["60"], "olive_hectares": [1.0]}
    )
    target = pd.DataFrame(
        {
            "province": "Jaén",
            "campaign": campaigns,
            "oil_final_t": 4e5,
            "method": ["reported_aica", *["derived_from_aforo"] * 5],
        }
    )
    aforo = target[["province", "campaign"]].assign(oil_aforo_t=4e5)
    table = province_table(municipal, climate, weights, target, aforo)
    assert set(table["target_method"]) == {"derived_from_aforo"}  # 2016/17 dropped: no lag
    assert "target_method" in cross_validate_ridge(table, alphas=(10.0,)).columns
