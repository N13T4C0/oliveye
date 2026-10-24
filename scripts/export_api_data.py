"""CLI: export the CSV files the API serves (see oliveye.api.app).

    uv run python scripts/export_api_data.py --results-dir ../oliveye-results \
        --model-run data/processed/model_run --out data/processed/api
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from oliveye.models.sources import load_aforo, load_monthly, load_weights
from oliveye.pipeline.production import final_production_series, target_series

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--model-run", type=Path, required=True)
    parser.add_argument("--sources-dir", type=Path, default=REPO_ROOT / "docs" / "sources")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "processed" / "api")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    monthly = load_monthly(args.results_dir)
    weights = load_weights(args.results_dir)
    names = pd.read_csv(
        sorted(args.results_dir.glob("*-catastro-ine-mapping/catastro_ine_municipalities.csv"))[-1],
        dtype=str,
    ).rename(columns={"catastro_code": "municipality_code"})
    processed = monthly[["province_code", "municipality_code"]].drop_duplicates()
    municipalities = weights.merge(
        names[["province_code", "municipality_code", "name"]],
        on=["province_code", "municipality_code"],
        how="left",
    ).merge(processed.assign(processed=True), how="left")
    municipalities["processed"] = municipalities["processed"].eq(True)
    municipalities["name"] = municipalities["name"].fillna(municipalities["municipality_code"])
    municipalities[
        ["province_code", "municipality_code", "name", "olive_hectares", "processed"]
    ].to_csv(args.out / "municipalities.csv", index=False)

    series = monthly[["province_code", "municipality_code", "month", "valid_cells"]].assign(
        month=monthly["month"].astype(str),
        ndvi=monthly["ndvi_clean"],  # outliers already removed
        ndmi=monthly["ndmi_clean"],
    )
    series.to_csv(args.out / "indices_monthly.csv", index=False)

    aforo = load_aforo(args.results_dir, args.sources_dir)
    pdf = pd.read_csv(sorted(args.results_dir.glob("*-aforo-table-*/aforo_by_province.csv"))[-1])
    press = pd.read_csv(args.sources_dir / "aforo_press_releases.csv")
    target = target_series(
        final_production_series(pdf, press),
        pd.read_csv(args.sources_dir / "production_reported.csv"),
    )
    predictions = pd.read_csv(args.model_run / "predictions.csv")[
        ["province", "campaign", "pred_t"]
    ]
    production = (
        target.merge(aforo[["province", "campaign", "oil_aforo_t"]], how="outer")
        .merge(predictions, how="left")
        .query("province in ['Jaén', 'Granada']")
    )
    production[["province", "campaign", "oil_final_t", "oil_aforo_t", "pred_t"]].to_csv(
        args.out / "production.csv", index=False
    )

    pd.read_csv(args.model_run / "summary.csv")[
        ["model", "rows", "mape_pct", "wins_vs_aforo"]
    ].to_csv(args.out / "summary.csv", index=False)
    print(f"API data written to {args.out}")


if __name__ == "__main__":
    main()
