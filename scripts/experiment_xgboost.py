"""Experiment (ADR 0004): XGBoost under the same leave-one-campaign-out as the main model.

A documented negative test: with ~16 rows a boosted tree ensemble has almost nothing to learn
from, so we expect it to be no better than the simple baselines. Run it to show the result, not
to pick it.

    uv sync --extra experiments
    uv run python scripts/experiment_xgboost.py --table data/processed/model_run/table.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from oliveye.models.evaluate import mape
from oliveye.models.train import MODEL_COLUMNS, loco_splits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, required=True)
    args = parser.parse_args()

    from xgboost import XGBRegressor  # optional dependency (extra "experiments")

    table = pd.read_csv(args.table)
    predictions = []
    for train_idx, test_idx in loco_splits(table):
        model = XGBRegressor(
            n_estimators=200, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=0
        )
        model.fit(table.loc[train_idx, MODEL_COLUMNS], table.loc[train_idx, "log_production"])
        pred = np.exp(model.predict(table.loc[test_idx, MODEL_COLUMNS]))
        predictions.append(pd.Series(pred, index=test_idx))
    pred_t = pd.concat(predictions).sort_index()
    print(f"rows: {len(table)}")
    print(f"XGBoost MAPE (leave-one-campaign-out): {mape(table['oil_final_t'], pred_t):.1f} %")
    print(
        f"Repeat last campaign MAPE:             "
        f"{mape(table['oil_final_t'], np.exp(table['lag_log_production'])):.1f} %"
    )


if __name__ == "__main__":
    main()
