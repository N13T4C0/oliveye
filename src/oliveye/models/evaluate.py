"""Metrics and intervals for out-of-sample predictions (ADR 0003, decisions 6 and 10)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def mape(actual: pd.Series, predicted: pd.Series) -> float:
    """Mean absolute percentage error, in percent (e.g. 400 vs 500 is 20 %)."""
    a = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(p - a) / a) * 100)


def interval_bounds(log_residuals: pd.Series, *, coverage: float = 0.8) -> tuple[float, float]:
    """Multiplicative interval from out-of-sample log residuals (log actual − log predicted).

    Returns (low, high) factors: a forecast F has the interval [F * low, F * high]. With ~16
    residuals this is rough, which is exactly why it must be shown.
    """
    tail = (1 - coverage) / 2
    low, high = np.quantile(np.asarray(log_residuals, dtype=float), [tail, 1 - tail])
    return float(np.exp(low)), float(np.exp(high))


def summarise(model_predictions: pd.DataFrame, baselines: pd.DataFrame) -> pd.DataFrame:
    """One row per model: rows evaluated, MAPE and campaigns closer than the aforo.

    Every model is compared on the rows where both it and the aforo have a value, so the
    win count is like-for-like.
    """
    merged = baselines.merge(
        model_predictions[["campaign", "province", "pred_t"]].rename(
            columns={"pred_t": "pred_ridge_t"}
        ),
        on=["campaign", "province"],
        how="left",
    )
    models = {
        "last_campaign": "pred_last_t",
        "mean_5_campaigns": "pred_mean5_t",
        "aforo": "pred_aforo_t",
        "ridge": "pred_ridge_t",
    }
    rows = []
    for name, column in models.items():
        valid = merged.dropna(subset=[column])
        error = (valid[column] - valid["oil_final_t"]).abs()
        both = valid.dropna(subset=["pred_aforo_t"])
        wins = int(
            (
                (both[column] - both["oil_final_t"]).abs()
                < (both["pred_aforo_t"] - both["oil_final_t"]).abs()
            ).sum()
        )
        rows.append(
            {
                "model": name,
                "rows": len(valid),
                "mape_pct": round(mape(valid["oil_final_t"], valid[column]), 1)
                if len(valid)
                else None,
                "median_abs_error_t": round(float(error.median()), -2) if len(valid) else None,
                "wins_vs_aforo": wins,
                "rows_with_aforo": len(both),
            }
        )
    return pd.DataFrame(rows)
