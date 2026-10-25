"""Load the modelling inputs from a checkout of the `results` branch plus `docs/sources/`.

Layout expected under `results_dir` (all produced by the job queue):

* `*-openeo-real-<prov>-<mun>-<period>/indices_monthly_*.csv` — monthly indices per municipality,
  one folder per extraction period in `INDEX_PERIODS`
* `*-open-meteo-daily-*/open_meteo_daily_*.csv` and `point_cells.csv` — ERA5 daily weather
* `*-sigpac-rank-<prov>/olive_ranking_<prov>.csv` — SIGPAC olive hectares per municipality
* `*-aforo-table-*/aforo_by_province.csv` — parsed aforo PDFs (2021/22 onwards)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from oliveye.models.dataset import climate_features, province_table
from oliveye.models.features import campaign_features
from oliveye.pipeline.openeo_indices import clean_monthly_indices
from oliveye.pipeline.production import final_production_series, target_series

PROVINCES = ("23", "18")


@dataclass(frozen=True)
class ModelInputs:
    monthly: pd.DataFrame
    climate: pd.DataFrame
    weights: pd.DataFrame
    target: pd.DataFrame
    aforo: pd.DataFrame


def _latest(paths: list[Path]) -> Path:
    if not paths:
        raise FileNotFoundError("Expected input not found in the results directory")
    return sorted(paths)[-1]


# Extraction periods, oldest first. 2016-2026 is the main run (120 months, the cap per job);
# 2015-2016 extends Sentinel-2 back to October 2015 (Sentinel-2A only) for campaign 2016/17.
INDEX_PERIODS: tuple[str, ...] = ("2015-2016", "2016-2026")
KEYS = ["province_code", "municipality_code", "month"]


def index_series_paths(results_dir: Path, filename_glob: str) -> list[Path]:
    """Files named `filename_glob` in the job folders of every period in `INDEX_PERIODS`.

    One-off test extractions (e.g. a single month) have other suffixes and are never read.
    """
    paths: list[Path] = []
    for period in INDEX_PERIODS:
        paths += sorted(results_dir.glob(f"*-openeo-real-*-{period}/{filename_glob}"))
    return paths


def load_monthly(results_dir: Path) -> pd.DataFrame:
    """Monthly indices of every municipality processed so far, re-cleaned causally.

    Periods are joined into one series per municipality before cleaning, so the outlier filter
    sees a continuous series across the join. If two periods share a month, the later period in
    `INDEX_PERIODS` (the main extraction) wins.

    The job outputs carry flags from a centred Hampel window (fine for exploring a series), which
    would let September/October images clean July/August values. Features stop in August, so the
    flags are recomputed here from the raw columns with a trailing window (no openEO request).
    """
    frames = []
    for path in index_series_paths(results_dir, "indices_monthly_*.csv"):
        frame = pd.read_csv(path, dtype={"province_code": str, "municipality_code": str})
        frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
        frames.append(
            frame.drop(columns=[c for c in frame.columns if c.endswith(("_outlier", "_clean"))])
        )
    if not frames:
        raise FileNotFoundError("No municipal index series found")
    raw = pd.concat(frames, ignore_index=True).drop_duplicates(KEYS, keep="last")
    return clean_monthly_indices(raw.sort_values(KEYS).reset_index(drop=True), causal=True)


def load_weights(results_dir: Path) -> pd.DataFrame:
    frames = []
    for code in PROVINCES:
        path = _latest(list(results_dir.glob(f"*-sigpac-rank-{code}/olive_ranking_{code}.csv")))
        frame = pd.read_csv(path, dtype={"municipality_code": str})
        frames.append(frame.assign(province_code=code))
    return pd.concat(frames, ignore_index=True)


def load_aforo(results_dir: Path, sources_dir: Path) -> pd.DataFrame:
    """Official aforo per province and campaign: PDFs first, then curated press releases."""
    pdf = pd.read_csv(_latest(list(results_dir.glob("*-aforo-table-*/aforo_by_province.csv"))))
    press = pd.read_csv(sources_dir / "aforo_press_releases.csv")
    columns = ["campaign", "province", "oil_aforo_t", "oil_var_prev_pct"]
    both = pd.concat([pdf[columns], press[columns]], ignore_index=True)
    return both.drop_duplicates(["campaign", "province"], keep="first")


def load_inputs(results_dir: Path, sources_dir: Path) -> ModelInputs:
    weather_dir = _latest(list(results_dir.glob("*-open-meteo-daily-*")))
    daily = pd.read_csv(_latest(list(weather_dir.glob("open_meteo_daily_*.csv"))))
    points = pd.read_csv(weather_dir / "point_cells.csv")
    aforo = load_aforo(results_dir, sources_dir)
    pdf = pd.read_csv(_latest(list(results_dir.glob("*-aforo-table-*/aforo_by_province.csv"))))
    press = pd.read_csv(sources_dir / "aforo_press_releases.csv")
    derived = final_production_series(pdf, press)
    target = target_series(derived, pd.read_csv(sources_dir / "production_reported.csv"))
    return ModelInputs(
        monthly=load_monthly(results_dir),
        climate=climate_features(daily, points),
        weights=load_weights(results_dir),
        target=target,
        aforo=aforo,
    )


def build_table(inputs: ModelInputs) -> pd.DataFrame:
    """Province × campaign table plus the share of olive area behind each row's features."""
    municipal = campaign_features(inputs.monthly)
    table = province_table(municipal, inputs.climate, inputs.weights, inputs.target, inputs.aforo)
    covered = (
        inputs.weights.merge(
            municipal[["province_code", "municipality_code"]].drop_duplicates(),
            on=["province_code", "municipality_code"],
        )
        .groupby("province_code")["olive_hectares"]
        .sum()
    )
    total = inputs.weights.groupby("province_code")["olive_hectares"].sum()
    share = (covered / total).rename(index={"23": "Jaén", "18": "Granada"})
    table["olive_area_covered"] = table["province"].map(share).round(3)
    return table
