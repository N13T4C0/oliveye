"""CLI: build the province × campaign table, run leave-one-campaign-out, write the results.

    git worktree add ../oliveye-results origin/results     # once
    uv run python scripts/train_models.py --results-dir ../oliveye-results

Writes to `--out` (default data/processed/model_run/, git-ignored): table.csv,
predictions.csv, corrector.csv, summary.csv and run.json. Logs to MLflow when it is installed.
Nothing is published automatically: results are reviewed (model-qa + auditor) before any of
them is copied to docs/results/.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from oliveye.models.evaluate import interval_bounds, summarise
from oliveye.models.sources import build_table, load_inputs
from oliveye.models.train import (
    baseline_predictions,
    cross_validate_aforo_corrector,
    cross_validate_ridge,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--sources-dir", type=Path, default=REPO_ROOT / "docs" / "sources")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "processed" / "model_run")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    table = build_table(load_inputs(args.results_dir, args.sources_dir))
    table.to_csv(args.out / "table.csv", index=False)
    print(table.round(3).to_string(index=False))

    ridge = cross_validate_ridge(table)
    corrector = cross_validate_aforo_corrector(table)
    baselines = baseline_predictions(table)
    summary = summarise(ridge, baselines)
    ridge.to_csv(args.out / "predictions.csv", index=False)
    corrector.to_csv(args.out / "corrector.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)

    residuals = np.log(ridge["oil_final_t"]) - ridge["pred_log"]
    low, high = interval_bounds(residuals, coverage=0.8)
    run = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": len(table),
        "campaigns": int(table["campaign"].nunique()),
        "olive_area_covered": table.groupby("province")["olive_area_covered"].first().to_dict(),
        "interval_80pct_factors": [round(low, 3), round(high, 3)],
        "alphas_chosen": sorted(ridge["alpha"].unique().tolist()),
    }
    (args.out / "run.json").write_text(json.dumps(run, indent=1), encoding="utf-8")
    print(summary.to_string(index=False))
    print(json.dumps(run, indent=1))

    try:
        import mlflow
    except ImportError:
        print("MLflow not installed: skipping experiment tracking")
        return
    mlflow.set_experiment("oliveye-province-production")
    with mlflow.start_run():
        mlflow.log_params({"rows": run["rows"], "campaigns": run["campaigns"]})
        for row in summary.itertuples(index=False):
            if row.mape_pct is not None:
                mlflow.log_metric(f"mape_{row.model}", float(row.mape_pct))
            mlflow.log_metric(f"wins_vs_aforo_{row.model}", float(row.wins_vs_aforo))
        mlflow.log_artifacts(str(args.out))


if __name__ == "__main__":
    main()
