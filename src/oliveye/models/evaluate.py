"""Metrics, intervals and tests for out-of-sample predictions (ADR 0003, decisions 6 and 10).

All comparisons are like-for-like: every model is scored on the same rows (those where every
model, including the aforo, has a value). Errors are also aggregated per campaign, because the
two provinces of a campaign share the same weather and are not independent evidence.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping

import numpy as np
import pandas as pd

MAX_SIGN_FLIP_N = 20  # 2**20 sign patterns is still instant; beyond that use a sampled test


def mape(actual: pd.Series, predicted: pd.Series) -> float:
    """Mean absolute percentage error, in percent (e.g. 400 vs 500 is 20 %)."""
    a = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(p - a) / a) * 100)


def interval_bounds(log_residuals: pd.Series, *, coverage: float = 0.8) -> tuple[float, float]:
    """Multiplicative interval from the empirical quantiles of log residuals (actual − pred).

    Returns (low, high) factors: a forecast F has the interval [F * low, F * high].
    """
    tail = (1 - coverage) / 2
    low, high = np.quantile(np.asarray(log_residuals, dtype=float), [tail, 1 - tail])
    return float(np.exp(low)), float(np.exp(high))


def conformal_half_width(log_residuals: pd.Series, *, coverage: float = 0.8) -> float:
    """Split-conformal half-width in log space: the ⌈(n+1)·coverage⌉-th smallest |residual|.

    A forecast F gets the symmetric multiplicative interval [F / e^q, F · e^q]. With n residuals
    the rank is capped at n, so the interval is never narrower than the data supports.
    """
    magnitudes = np.sort(np.abs(np.asarray(log_residuals, dtype=float)))
    n = len(magnitudes)
    if n == 0:
        raise ValueError("no residuals")
    rank = min(math.ceil(round((n + 1) * coverage, 9)), n)
    return float(magnitudes[rank - 1])


def sign_flip_p_value(differences: pd.Series) -> float:
    """Exact two-sided sign-flip (permutation) test that the mean difference is zero.

    `differences` are paired, e.g. per campaign: model error − aforo error. Under the null each
    sign is equally likely, so p = share of the 2**n sign patterns whose |sum| ≥ the observed.
    """
    d = np.asarray(differences, dtype=float)
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return 1.0
    if n > MAX_SIGN_FLIP_N:
        raise ValueError(f"exact test limited to {MAX_SIGN_FLIP_N} pairs, got {n}")
    observed = abs(d.sum()) - 1e-12
    signs = np.array(list(itertools.product((-1.0, 1.0), repeat=n)))
    return float(np.mean(np.abs(signs @ d) >= observed))


def _merged(
    model_predictions: pd.DataFrame,
    baselines: pd.DataFrame,
    others: Mapping[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict[str, str]]:
    keys = ["campaign", "province"]
    merged = baselines.copy()
    models = {
        "last_campaign": "pred_last_t",
        "mean_5_campaigns": "pred_mean5_t",
        "province_mean": "pred_province_mean_t",
        "aforo": "pred_aforo_t",
    }
    for name, frame in {"ridge": model_predictions, **others}.items():
        column = f"pred_{name}_t"
        merged = merged.merge(
            frame[[*keys, "pred_t"]].rename(columns={"pred_t": column}), on=keys, how="left"
        )
        models[name] = column
    models = {name: column for name, column in models.items() if column in merged}
    common = merged.dropna(subset=list(models.values()))
    return common, models


def per_campaign_errors(
    model_predictions: pd.DataFrame,
    baselines: pd.DataFrame,
    others: Mapping[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Mean absolute log error per campaign (both provinces averaged), one column per model."""
    common, models = _merged(model_predictions, baselines, others or {})
    log_truth = np.log(common["oil_final_t"])
    errors = pd.DataFrame(
        {name: (np.log(common[column]) - log_truth).abs() for name, column in models.items()}
    )
    errors["campaign"] = common["campaign"].to_numpy()
    return errors.groupby("campaign").mean()


def summarise(
    model_predictions: pd.DataFrame,
    baselines: pd.DataFrame,
    others: Mapping[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """One row per model, all scored on the same rows.

    Columns: rows, MAPE, median APE, mean |log error|, median absolute error (t), rows and
    campaigns closer than the aforo, and the exact sign-flip p-value of the per-campaign
    difference in |log error| against the aforo (small p: the difference is unlikely to be luck).
    """
    common, models = _merged(model_predictions, baselines, others or {})
    by_campaign = per_campaign_errors(model_predictions, baselines, others)
    truth = common["oil_final_t"]
    aforo_error = (common["pred_aforo_t"] - truth).abs()
    rows = []
    for name, column in models.items():
        pred = common[column]
        abs_error = (pred - truth).abs()
        campaign_diff = by_campaign[name] - by_campaign["aforo"]
        rows.append(
            {
                "model": name,
                "rows": len(common),
                "campaigns": len(by_campaign),
                "mape_pct": round(mape(truth, pred), 1) if len(common) else None,
                "median_ape_pct": round(float((abs_error / truth).median() * 100), 1)
                if len(common)
                else None,
                "mean_abs_log_error": round(float((np.log(pred) - np.log(truth)).abs().mean()), 3)
                if len(common)
                else None,
                "median_abs_error_t": round(float(abs_error.median()), -2) if len(common) else None,
                "wins_vs_aforo": int((abs_error < aforo_error).sum()),
                "campaign_wins_vs_aforo": int((campaign_diff < 0).sum()),
                "p_vs_aforo": None
                if name == "aforo"
                else round(sign_flip_p_value(campaign_diff), 3),
            }
        )
    return pd.DataFrame(rows)
