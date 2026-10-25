"""CLI: dated forecast of a campaign whose production is not known yet (ADR 0003 #15).

    uv run python scripts/forecast.py --results-dir ../oliveye-results --campaign 2026/27

Fits the main model on every known campaign, predicts the requested campaign with data up to
August, and attaches the conformal-style 80 % interval from the leave-one-campaign-out
residuals. Writes `data/processed/forecast_<campaign>.csv` and `.json` (git-ignored); the
reviewed figures are copied to docs/results/ by hand, with their date, before the real
production is known.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from oliveye.models.dataset import forecast_rows
from oliveye.models.evaluate import conformal_half_width
from oliveye.models.features import campaign_features
from oliveye.models.sources import build_table, load_inputs
from oliveye.models.train import cross_validate_ridge, forecast

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--campaign", required=True, help='e.g. "2026/27"')
    parser.add_argument("--sources-dir", type=Path, default=REPO_ROOT / "docs" / "sources")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "processed")
    args = parser.parse_args()

    inputs = load_inputs(args.results_dir, args.sources_dir)
    table = build_table(inputs)
    if args.campaign in set(table["campaign"]):
        raise SystemExit(f"{args.campaign} already has a known production: not a forecast")

    residuals = (
        np.log(table["oil_final_t"].to_numpy())
        - cross_validate_ridge(table)
        .set_index(["campaign", "province"])
        .loc[list(zip(table["campaign"], table["province"], strict=True)), "pred_log"]
        .to_numpy()
    )
    factor = float(np.exp(conformal_half_width(residuals, coverage=0.8)))

    rows = forecast_rows(
        campaign_features(inputs.monthly),
        inputs.climate,
        inputs.weights,
        inputs.target,
        inputs.aforo,
        campaign=args.campaign,
    )
    result = forecast(table, rows, interval_factor=factor)
    result["lag_t"] = rows["lag_t"].to_numpy()

    stem = f"forecast_{args.campaign.replace('/', '-')}"
    args.out.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out / f"{stem}.csv", index=False)
    meta = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "campaign": args.campaign,
        "data_cut": "August of the campaign's first year",
        "training_rows": len(table),
        "training_campaigns": int(table["campaign"].nunique()),
        "interval": "80 % conformal-style, from leave-one-campaign-out residuals",
        "interval_factor": round(factor, 3),
    }
    (args.out / f"{stem}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(result.round(0).to_string(index=False))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
