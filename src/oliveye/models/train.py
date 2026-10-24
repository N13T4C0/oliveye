"""Leave-one-campaign-out training: baselines, Ridge and the aforo corrector (ADR 0003).

Every evaluation holds out one whole campaign (both provinces). Inside each fold, Ridge's alpha
is chosen by a second leave-one-campaign-out over the training campaigns only, and the scaler
is fitted on the training rows only (it lives inside the sklearn Pipeline). The held-out target
is therefore never seen, directly or through preprocessing.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from oliveye.models.dataset import FEATURES

ALPHAS: tuple[float, ...] = (0.1, 1.0, 10.0)
MODEL_COLUMNS: list[str] = [*FEATURES, "is_granada"]
CORRECTOR_COLUMNS: list[str] = ["log_aforo", "is_granada"]


def loco_splits(table: pd.DataFrame) -> Iterator[tuple[pd.Index, pd.Index]]:
    """(train index, test index) per campaign; the test set is the whole campaign."""
    for campaign in sorted(table["campaign"].unique()):
        test = table.index[table["campaign"] == campaign]
        train = table.index[table["campaign"] != campaign]
        yield train, test


def make_pipeline(alpha: float) -> Pipeline:
    return Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])


def choose_alpha(train: pd.DataFrame, columns: Sequence[str], alphas: Sequence[float]) -> float:
    """Alpha with the lowest inner leave-one-campaign-out squared error (log scale)."""
    if train["campaign"].nunique() < 3:
        return 1.0
    errors = []
    for alpha in alphas:
        squared = []
        for inner_train, inner_test in loco_splits(train):
            model = make_pipeline(alpha).fit(
                train.loc[inner_train, list(columns)], train.loc[inner_train, "log_production"]
            )
            pred = model.predict(train.loc[inner_test, list(columns)])
            squared.extend((pred - train.loc[inner_test, "log_production"].to_numpy()) ** 2)
        errors.append(float(np.mean(squared)))
    return float(alphas[int(np.argmin(errors))])


def _cross_validate(
    table: pd.DataFrame, columns: Sequence[str], alphas: Sequence[float]
) -> pd.DataFrame:
    rows = []
    for train_idx, test_idx in loco_splits(table):
        train = table.loc[train_idx]
        alpha = choose_alpha(train, columns, alphas)
        model = make_pipeline(alpha).fit(train[list(columns)], train["log_production"])
        test = table.loc[test_idx]
        pred_log = model.predict(test[list(columns)])
        for (_, row), value in zip(test.iterrows(), pred_log, strict=True):
            rows.append(
                {
                    "campaign": row["campaign"],
                    "province": row["province"],
                    "oil_final_t": row["oil_final_t"],
                    "pred_log": float(value),
                    "pred_t": float(np.exp(value)),
                    "alpha": alpha,
                }
            )
    return pd.DataFrame(rows)


def cross_validate_ridge(table: pd.DataFrame, *, alphas: Sequence[float] = ALPHAS) -> pd.DataFrame:
    """Out-of-sample predictions of the main model (independent of the aforo)."""
    return _cross_validate(table, MODEL_COLUMNS, alphas)


def cross_validate_aforo_corrector(
    table: pd.DataFrame, *, alphas: Sequence[float] = ALPHAS
) -> pd.DataFrame:
    """Secondary experiment: learn to correct the aforo (rows without aforo are skipped)."""
    with_aforo = table.dropna(subset=["oil_aforo_t"]).assign(
        log_aforo=lambda t: np.log(t["oil_aforo_t"])
    )
    return _cross_validate(with_aforo, CORRECTOR_COLUMNS, alphas)


def baseline_predictions(table: pd.DataFrame) -> pd.DataFrame:
    """Last campaign, mean of the previous five campaigns and the official aforo."""
    return pd.DataFrame(
        {
            "campaign": table["campaign"],
            "province": table["province"],
            "oil_final_t": table["oil_final_t"],
            "pred_last_t": np.exp(table["lag_log_production"]),
            "pred_mean5_t": table["mean5_t"],
            "pred_aforo_t": table["oil_aforo_t"],
        }
    ).reset_index(drop=True)


def fit_final(table: pd.DataFrame, *, alphas: Sequence[float] = ALPHAS) -> tuple[Pipeline, float]:
    """Main model fitted on every campaign (alpha by leave-one-campaign-out), for forecasts."""
    alpha = choose_alpha(table, MODEL_COLUMNS, alphas)
    return make_pipeline(alpha).fit(table[MODEL_COLUMNS], table["log_production"]), alpha
