"""Leave-one-campaign-out training: baselines, Ridge and the aforo corrector (ADR 0003).

Validation rules (ADR 0003 and its 2026-10-25 amendment):

* One whole campaign (both provinces) is held out per fold. Campaign t+1 is also removed from
  that fold's training set, because its lag feature *is* campaign t's real production.
* Ridge's alpha is chosen by the same procedure inside the training campaigns only (nested),
  on a log-spaced grid with the one-standard-error rule (prefer more shrinkage when tied).
* The model (`ProvinceAnomalyRidge`) keeps each province's mean level unpenalised and fits
  Ridge to within-province anomalies: features are centred on their province mean, clipped to
  the training range (no extrapolation beyond what the model has seen) and standardised. Every
  step is fitted on the training rows only. Infinite shrinkage gives the province mean.
* A forward-chaining check (train only on earlier campaigns) is reported as well, because
  leave-one-campaign-out also trains on future years.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from oliveye.models.dataset import FEATURES, next_campaign

ALPHAS: tuple[float, ...] = tuple(float(a) for a in np.logspace(-1, 3, 9))
MODEL_COLUMNS: list[str] = [*FEATURES, "is_granada"]
LAG_ONLY_COLUMNS: list[str] = ["lag_log_production", "is_granada"]
CORRECTOR_COLUMNS: list[str] = ["log_aforo", "is_granada"]

Splitter = Callable[[pd.DataFrame], Iterator[tuple[pd.Index, pd.Index]]]


def loco_splits(table: pd.DataFrame) -> Iterator[tuple[pd.Index, pd.Index]]:
    """(train index, test index) per campaign; training excludes the campaign and the next one."""
    for campaign in sorted(table["campaign"].unique()):
        excluded = {campaign, next_campaign(campaign)}
        test = table.index[table["campaign"] == campaign]
        train = table.index[~table["campaign"].isin(excluded)]
        yield train, test


def forward_splits(
    table: pd.DataFrame, *, min_train_campaigns: int = 4
) -> Iterator[tuple[pd.Index, pd.Index]]:
    """Train on earlier campaigns only (a stricter, time-respecting check).

    Used for the outer folds only: inside each one, alpha is still chosen by leave-one-campaign-out
    among those earlier campaigns (only past data, but enough folds to choose from).
    """
    for campaign in sorted(table["campaign"].unique()):
        train = table.index[table["campaign"] < campaign]
        if table.loc[train, "campaign"].nunique() < min_train_campaigns:
            continue
        yield train, table.index[table["campaign"] == campaign]


class ProvinceCentering(BaseEstimator, TransformerMixin):  # type: ignore[misc]
    """Subtract each province's training mean from every feature except `is_granada`."""

    def fit(self, X: pd.DataFrame, y: object = None) -> ProvinceCentering:  # noqa: N803
        features = [c for c in X.columns if c != "is_granada"]
        self.means_ = X.groupby("is_granada")[features].mean()
        self.global_mean_ = X[features].mean()
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
        out = X.copy()
        for column in self.means_.columns:
            province_mean = X["is_granada"].map(self.means_[column])
            out[column] = X[column] - province_mean.fillna(self.global_mean_[column])
        return out


class RangeClipper(BaseEstimator, TransformerMixin):  # type: ignore[misc]
    """Clip each feature to the [min, max] seen in training: no extrapolation."""

    def fit(self, X: pd.DataFrame, y: object = None) -> RangeClipper:  # noqa: N803
        self.low_ = X.min()
        self.high_ = X.max()
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
        return X.clip(lower=self.low_, upper=self.high_, axis=1)


class ProvinceAnomalyRidge(BaseEstimator, RegressorMixin):  # type: ignore[misc]
    """Ridge on within-province anomalies, with an unpenalised province level.

    Fit: subtract each province's training mean from the target and the features, clip the
    features to their training range, standardise them and fit Ridge without an intercept.
    Predict: province mean + Ridge(anomalies). As alpha grows the prediction tends to the
    province mean, never to a pooled mean of the two provinces.
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    def _features(self, X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
        return X.drop(columns="is_granada")

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ProvinceAnomalyRidge:  # noqa: N803
        target = pd.Series(np.asarray(y, dtype=float), index=X.index)
        self.level_ = target.groupby(X["is_granada"]).mean()
        self.feature_names_ = list(self._features(X).columns)
        self.transform_ = Pipeline(
            [("centre", ProvinceCentering()), ("clip", RangeClipper()), ("scale", StandardScaler())]
        )
        anomaly = target - self._level(X)
        self.ridge_ = Ridge(alpha=self.alpha, fit_intercept=False)
        if self.feature_names_:
            self.ridge_.fit(self._transform(X, fit=True), anomaly.to_numpy())
        return self

    def _level(self, X: pd.DataFrame) -> pd.Series:  # noqa: N803
        level = X["is_granada"].map(self.level_)
        if level.isna().any():
            raise ValueError("cannot predict a province that is absent from the training rows")
        return level.astype(float)

    def _transform(self, X: pd.DataFrame, *, fit: bool = False) -> np.ndarray:  # noqa: N803
        if fit:
            out = self.transform_.fit_transform(X)
        else:
            out = self.transform_.transform(X)
        frame = pd.DataFrame(out, columns=list(X.columns), index=X.index)
        return np.asarray(self._features(frame), dtype=float)

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        level = self._level(X).to_numpy()
        if not self.feature_names_:
            return level
        return np.asarray(level + self.ridge_.predict(self._transform(X)), dtype=float)

    @property
    def coef_(self) -> dict[str, float]:
        """Standardised anomaly slopes, plus `level_gap_granada`: the unpenalised log-level gap
        Granada − Jaén (a different unit, kept apart by its name)."""
        slopes = self.ridge_.coef_.tolist() if self.feature_names_ else []
        coefs = dict(zip(self.feature_names_, slopes, strict=True))
        coefs["level_gap_granada"] = float(self.level_.get(1, np.nan) - self.level_.get(0, np.nan))
        return coefs


def make_pipeline(alpha: float) -> ProvinceAnomalyRidge:
    return ProvinceAnomalyRidge(alpha=alpha)


def choose_alpha(
    train: pd.DataFrame,
    columns: Sequence[str],
    alphas: Sequence[float],
    splitter: Splitter = loco_splits,
) -> float:
    """Largest alpha whose inner-fold error is within one standard error of the best."""
    if train["campaign"].nunique() < 4:
        return float(max(alphas))
    means, ses = [], []
    for alpha in alphas:
        fold_errors = []
        for inner_train, inner_test in splitter(train):
            model = make_pipeline(alpha).fit(
                train.loc[inner_train, list(columns)], train.loc[inner_train, "log_production"]
            )
            pred = model.predict(train.loc[inner_test, list(columns)])
            truth = train.loc[inner_test, "log_production"].to_numpy()
            fold_errors.append(float(np.mean((pred - truth) ** 2)))
        if len(fold_errors) < 2:  # no standard error without two folds: shrink fully
            return float(max(alphas))
        means.append(float(np.mean(fold_errors)))
        ses.append(float(np.std(fold_errors, ddof=1) / np.sqrt(len(fold_errors))))
    best = int(np.argmin(means))
    threshold = means[best] + ses[best]
    eligible = [a for a, m in zip(alphas, means, strict=True) if m <= threshold]
    return float(max(eligible))


def _cross_validate(
    table: pd.DataFrame,
    columns: Sequence[str],
    alphas: Sequence[float],
    splitter: Splitter = loco_splits,
) -> pd.DataFrame:
    rows = []
    for train_idx, test_idx in splitter(table):
        train = table.loc[train_idx]
        alpha = choose_alpha(train, columns, alphas)
        model = make_pipeline(alpha).fit(train[list(columns)], train["log_production"])
        coefs = model.coef_
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
                    **{f"coef_{name}": float(c) for name, c in coefs.items()},
                }
            )
    return pd.DataFrame(rows)


def cross_validate_ridge(
    table: pd.DataFrame, *, alphas: Sequence[float] = ALPHAS, splitter: Splitter = loco_splits
) -> pd.DataFrame:
    """Out-of-sample predictions of the main model (independent of the aforo)."""
    return _cross_validate(table, MODEL_COLUMNS, alphas, splitter)


def cross_validate_lag_only(
    table: pd.DataFrame, *, alphas: Sequence[float] = ALPHAS
) -> pd.DataFrame:
    """Reference: last campaign + province only, to see whether the satellite/climate help."""
    return _cross_validate(table, LAG_ONLY_COLUMNS, alphas)


def cross_validate_aforo_corrector(
    table: pd.DataFrame, *, alphas: Sequence[float] = ALPHAS
) -> pd.DataFrame:
    """Secondary experiment: learn to correct the aforo (rows without aforo are skipped).

    It has no lag feature, so dropping campaign t+1 is not needed here; it is kept so that every
    model is validated with the same splits.
    """
    with_aforo = table.dropna(subset=["oil_aforo_t"]).assign(
        log_aforo=lambda t: np.log(t["oil_aforo_t"])
    )
    return _cross_validate(with_aforo, CORRECTOR_COLUMNS, alphas)


def province_mean_predictions(table: pd.DataFrame) -> pd.Series:
    """Reference: mean log production of the province in each fold's training campaigns."""
    predictions = pd.Series(index=table.index, dtype=float)
    for train_idx, test_idx in loco_splits(table):
        means = table.loc[train_idx].groupby("province")["log_production"].mean()
        level = table.loc[test_idx, "province"].map(means)
        if level.isna().any():
            raise ValueError("a held-out province has no training rows")
        predictions.loc[test_idx] = np.exp(level)
    return predictions


def baseline_predictions(table: pd.DataFrame) -> pd.DataFrame:
    """Last campaign, mean of the previous five campaigns, province mean and the aforo."""
    return pd.DataFrame(
        {
            "campaign": table["campaign"],
            "province": table["province"],
            "oil_final_t": table["oil_final_t"],
            "pred_last_t": np.exp(table["lag_log_production"]),
            "pred_mean5_t": table["mean5_t"],
            "pred_province_mean_t": province_mean_predictions(table),
            "pred_aforo_t": table["oil_aforo_t"],
        }
    ).reset_index(drop=True)


def fit_final(
    table: pd.DataFrame, *, alphas: Sequence[float] = ALPHAS
) -> tuple[ProvinceAnomalyRidge, float]:
    """Main model fitted on every campaign (alpha by the same nested rule), for forecasts."""
    alpha = choose_alpha(table, MODEL_COLUMNS, alphas)
    return make_pipeline(alpha).fit(table[MODEL_COLUMNS], table["log_production"]), alpha
