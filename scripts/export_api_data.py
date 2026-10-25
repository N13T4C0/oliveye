"""CLI: export the small JSON files the deployable API serves (api/oliveye_api.py).

    uv run python scripts/export_api_data.py --results-dir ../oliveye-results \
        --model-run data/processed/model_run --forecast data/processed/forecast_2026-27

Writes to `api/data/` (committed: small, derived from public sources, reviewed like
docs/results/). Raw and interim data stay in data/ and out of git.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from oliveye.models.features import campaign_features
from oliveye.models.sources import load_aforo, load_monthly, load_weights
from oliveye.pipeline.olive_grid import municipality_footprints
from oliveye.pipeline.production import final_production_series, target_series
from oliveye.pipeline.publish import display_name, map_features, records

REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_COLUMNS = ["ndvi_spring", "ndvi_summer", "ndmi_summer"]
PROVINCES = ["Jaén", "Granada"]


def _write(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{path.relative_to(REPO_ROOT)}: {path.stat().st_size / 1e3:.0f} kB")


def municipality_names(results_dir: Path, sources_dir: Path) -> dict[tuple[str, str], str]:
    """(province, Catastro code) -> official INE name with accents, article in front."""
    mapping = pd.read_csv(
        sorted(results_dir.glob("*-catastro-ine-mapping/catastro_ine_municipalities.csv"))[-1],
        dtype=str,
    )
    ine = pd.read_csv(sources_dir / "ine_municipality_names.csv", dtype=str)
    named = mapping.merge(ine, on=["province_code", "ine_code"], how="left", suffixes=("_cat", ""))
    named["name"] = named["name"].fillna(named["name_cat"].str.title())
    return {
        (row.province_code, row.catastro_code): display_name(row.name)
        for row in named.itertuples(index=False)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--model-run", type=Path, required=True)
    parser.add_argument("--forecast", type=Path, required=True, help="path without extension")
    parser.add_argument("--sources-dir", type=Path, default=REPO_ROOT / "docs" / "sources")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "api" / "data")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    names = municipality_names(args.results_dir, args.sources_dir)
    monthly = load_monthly(args.results_dir)  # outliers re-flagged causally
    weights = load_weights(args.results_dir)
    keys = ["province_code", "municipality_code"]

    processed = set(map(tuple, monthly[keys].drop_duplicates().to_numpy()))
    municipalities = weights[[*keys, "olive_hectares"]].copy()
    municipalities["name"] = [
        names.get((p, m), m)
        for p, m in zip(weights["province_code"], weights["municipality_code"], strict=True)
    ]
    municipalities["processed"] = [
        (p, m) in processed
        for p, m in zip(weights["province_code"], weights["municipality_code"], strict=True)
    ]
    municipalities["olive_hectares"] = municipalities["olive_hectares"].round(1)
    _write(args.out / "municipalities.json", records(municipalities))

    series = monthly.assign(
        month=monthly["month"].astype(str),
        ndvi=monthly["ndvi_clean"].round(4),
        ndmi=monthly["ndmi_clean"].round(4),
    )
    indices = {
        f"{p}-{m}": records(group[["month", "ndvi", "ndmi", "valid_cells"]].sort_values("month"))
        for (p, m), group in series.groupby(keys)
    }
    _write(args.out / "indices.json", indices)

    aforo = load_aforo(args.results_dir, args.sources_dir)
    pdf = pd.read_csv(sorted(args.results_dir.glob("*-aforo-table-*/aforo_by_province.csv"))[-1])
    press = pd.read_csv(args.sources_dir / "aforo_press_releases.csv")
    target = target_series(
        final_production_series(pdf, press),
        pd.read_csv(args.sources_dir / "production_reported.csv"),
    ).rename(columns={"method": "target_method"})
    predictions = pd.read_csv(args.model_run / "predictions.csv")[
        ["province", "campaign", "pred_t"]
    ]
    production = (
        target[["province", "campaign", "oil_final_t", "target_method"]]
        .merge(aforo[["province", "campaign", "oil_aforo_t"]], how="outer")
        .merge(predictions, how="left")
    )
    _write(
        args.out / "production.json",
        {
            province: records(
                production[production["province"] == province]
                .sort_values("campaign")[
                    ["campaign", "oil_final_t", "oil_aforo_t", "pred_t", "target_method"]
                ]
                .round({"pred_t": -2})
            )
            for province in PROVINCES
        },
    )

    summary = pd.read_csv(args.model_run / "summary.csv")
    _write(
        args.out / "summary.json",
        records(
            summary[
                ["model", "rows", "campaigns", "mape_pct", "campaign_wins_vs_aforo", "p_vs_aforo"]
            ]
        ),
    )

    meta = json.loads(args.forecast.with_suffix(".json").read_text(encoding="utf-8"))
    rows = pd.read_csv(args.forecast.with_suffix(".csv"))
    _write(
        args.out / "forecast.json",
        {
            "campaign": meta["campaign"],
            "published": meta["created_at"][:10],
            "interval_factor": meta["interval_factor"],
            "rows": records(
                rows[["province", "pred_t", "low_t", "high_t", "oil_aforo_t"]].round(-2)
            ),
        },
    )

    cells = gpd.GeoDataFrame(
        pd.concat(
            [
                gpd.read_file(path)
                # Footprints from the main extraction: every period uses the same SIGPAC grid.
                for path in sorted(args.results_dir.glob("*-openeo-real-*-2016-2026/cells.geojson"))
            ],
            ignore_index=True,
        ),
        crs="EPSG:4326",
    )
    seasonal = campaign_features(monthly)
    seasonal[MAP_COLUMNS] = seasonal[MAP_COLUMNS].round(4)
    _write(
        args.out / "map.geojson",
        map_features(municipality_footprints(cells), seasonal, names, MAP_COLUMNS),
    )


if __name__ == "__main__":
    main()
