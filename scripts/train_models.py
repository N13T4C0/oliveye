"""CLI: build the province × campaign table, run leave-one-campaign-out, write the results.

    git worktree add ../oliveye-results origin/results     # once
    uv run python scripts/train_models.py --results-dir ../oliveye-results

Writes to `--out` (default data/processed/model_run/, git-ignored): table.csv,
predictions.csv, lag_only.csv, forward.csv, corrector.csv, summary.csv,
per_campaign.csv and run.json. Logs to a local MLflow store
(data/mlflow/, git-ignored) when the `tracking` extra is installed.
Nothing is published automatically: results are reviewed (model-qa + auditor) before any of
them is copied to docs/results/.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from oliveye.models.evaluate import (
    conformal_half_width,
    interval_bounds,
    per_campaign_errors,
    summarise,
)
from oliveye.models.sources import build_table, load_inputs
from oliveye.models.train import (
    baseline_predictions,
    cross_validate_aforo_corrector,
    cross_validate_lag_only,
    cross_validate_ridge,
    forward_splits,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--sources-dir", type=Path, default=REPO_ROOT / "docs" / "sources")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "processed" / "model_run")
    parser.add_argument("--mlflow-dir", type=Path, default=REPO_ROOT / "data" / "mlflow")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    table = build_table(load_inputs(args.results_dir, args.sources_dir))
    table.to_csv(args.out / "table.csv", index=False)
    print(table.round(3).to_string(index=False))

    ridge = cross_validate_ridge(table)
    lag_only = cross_validate_lag_only(table)
    forward = cross_validate_ridge(table, splitter=forward_splits)
    corrector = cross_validate_aforo_corrector(table)
    baselines = baseline_predictions(table)
    others = {"lag_only": lag_only}
    summary = summarise(ridge, baselines, others)
    per_campaign = per_campaign_errors(ridge, baselines, others)
    # Forward-chaining check: scored on its own (fewer) campaigns, against the same baselines.
    forward_summary = summarise(forward, baselines).query("model in ['ridge', 'aforo']")
    for name, frame in {
        "predictions": ridge,
        "lag_only": lag_only,
        "forward": forward,
        "corrector": corrector,
        "summary": summary,
        "forward_summary": forward_summary,
    }.items():
        frame.to_csv(args.out / f"{name}.csv", index=False)
    per_campaign.round(4).to_csv(args.out / "per_campaign.csv")

    residuals = np.log(ridge["oil_final_t"]) - ridge["pred_log"]
    low, high = interval_bounds(residuals, coverage=0.8)
    half_width = conformal_half_width(residuals, coverage=0.8)
    run = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": len(table),
        "campaigns": int(table["campaign"].nunique()),
        "olive_area_covered": table.groupby("province")["olive_area_covered"].first().to_dict(),
        "interval_80pct_quantile_factors": [round(low, 3), round(high, 3)],
        "interval_80pct_conformal_factor": round(float(np.exp(half_width)), 3),
        "alphas_chosen": sorted(round(a, 3) for a in ridge["alpha"].unique()),
        "coefficients_by_fold": ridge.drop_duplicates("campaign")
        .filter(like="coef_")
        .describe()
        .round(3)
        .to_dict(),
    }
    (args.out / "run.json").write_text(json.dumps(run, indent=1), encoding="utf-8")
    print(summary.to_string(index=False))
    print("Forward-chaining (past only):")
    print(forward_summary.to_string(index=False))
    print(per_campaign.round(3).to_string())
    print(json.dumps(run, indent=1))

    log_to_mlflow(run, summary, args.out, args.mlflow_dir)


def log_to_mlflow(run: dict[str, Any], summary: pd.DataFrame, out: Path, mlflow_dir: Path) -> None:
    """Record the run in a local MLflow store (SQLite + artifacts under data/, git-ignored)."""
    try:
        import mlflow
    except ImportError:
        print("MLflow not installed (uv sync --extra tracking): skipping experiment tracking")
        return
    mlflow_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{mlflow_dir / 'mlflow.db'}")
    name = "oliveye-province-production"
    if mlflow.get_experiment_by_name(name) is None:
        mlflow.create_experiment(name, artifact_location=(mlflow_dir / "artifacts").as_uri())
    mlflow.set_experiment(name)
    with mlflow.start_run():
        mlflow.log_params(
            {
                "rows": run["rows"],
                "campaigns": run["campaigns"],
                "validation": "leave-one-campaign-out (t and t+1 held out)",
                **{f"olive_area_{k}": v for k, v in run["olive_area_covered"].items()},
            }
        )
        for row in summary.itertuples(index=False):
            for metric in ("mape_pct", "mean_abs_log_error", "campaign_wins_vs_aforo"):
                value = getattr(row, metric)
                if pd.notna(value):
                    mlflow.log_metric(f"{metric}_{row.model}", float(value))
        mlflow.log_artifacts(str(out))


if __name__ == "__main__":
    main()
