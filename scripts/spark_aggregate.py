"""CLI (phase 2): per-cell series of all processed municipalities → Parquet + municipal means.

    uv sync --extra bigdata
    uv run python scripts/spark_aggregate.py --results-dir ../oliveye-results

Layers written (git-ignored):
* data/interim/cells.parquet           every cell-month with its province, municipality and
                                       olive hectares, partitioned by province;
* data/processed/municipal_monthly.parquet   olive-weighted monthly NDVI/NDMI per municipality.

It then checks parity against the per-municipality outputs the job queue produced with pandas
(`indices_monthly_*.csv`) and prints timings next to a pandas baseline over the same files.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from oliveye.models.sources import index_series_paths
from oliveye.pipeline.olive_grid import aggregate_cells
from oliveye.spark.cells import (
    KEYS,
    aggregate_municipal,
    read_cell_series,
    spark_session,
    write_parquet,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def cell_metadata(results_dir: Path) -> pd.DataFrame:
    """Cell weights from the main extraction (every period uses the same SIGPAC grid)."""
    frames = [
        pd.DataFrame(gpd.read_file(path).drop(columns="geometry"))
        for path in sorted(results_dir.glob("*-openeo-real-*-2016-2026/cells.geojson"))
    ]
    meta = pd.concat(frames, ignore_index=True)[["cell_id", *KEYS, "olive_ha"]]
    return meta.astype({"province_code": str, "municipality_code": str})


def pandas_baseline(results_dir: Path, meta: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """The pre-Spark way: read each municipality's CSV and aggregate it with pandas."""
    start = time.perf_counter()
    frames = []
    cells = gpd.GeoDataFrame(meta)
    for path in index_series_paths(results_dir, "indices_cells_*.csv"):
        frames.append(aggregate_cells(pd.read_csv(path), cells))
    return pd.concat(frames, ignore_index=True), time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    args = parser.parse_args()

    meta = cell_metadata(args.results_dir)
    spark = spark_session()
    spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "true")
    timings: dict[str, float] = {}

    start = time.perf_counter()
    metadata = spark.createDataFrame(meta)
    cells = read_cell_series(spark, args.results_dir)
    enriched = cells.join(metadata.select("cell_id", *KEYS, "olive_ha"), on="cell_id", how="inner")
    write_parquet(enriched, args.data_dir / "interim" / "cells.parquet", ["province_code"])
    timings["csv → partitioned Parquet"] = time.perf_counter() - start

    # Periods must not overlap, and every cell of every period must have its olive weight:
    # pandas (load_monthly) would silently drop a duplicate month, Spark would count it twice.
    total, distinct = cells.count(), cells.select("cell_id", "month").distinct().count()
    kept = spark.read.parquet(str(args.data_dir / "interim" / "cells.parquet")).count()
    if total != distinct:
        raise SystemExit(f"{total - distinct} duplicate cell-months across extraction periods")
    if kept != total:
        raise SystemExit(f"{total - kept} cell-months have no cell metadata (SIGPAC grid changed?)")

    start = time.perf_counter()
    stored = spark.read.parquet(str(args.data_dir / "interim" / "cells.parquet"))
    rows = stored.count()
    municipal = aggregate_municipal(stored.select("month", "cell_id", "ndvi", "ndmi"), metadata)
    write_parquet(municipal, args.data_dir / "processed" / "municipal_monthly.parquet")
    timings["Parquet → municipal means"] = time.perf_counter() - start

    result = pd.read_parquet(args.data_dir / "processed" / "municipal_monthly.parquet")
    spark.stop()

    # Parity with what the job queue produced (pandas, one municipality at a time).
    expected = pd.concat(
        [
            pd.read_csv(path, dtype={"province_code": str, "municipality_code": str})
            for path in index_series_paths(args.results_dir, "indices_monthly_*.csv")
        ],
        ignore_index=True,
    )[["month", *KEYS, "ndvi", "ndmi", "valid_cells"]]
    merged = expected.merge(
        result, on=["month", *KEYS], suffixes=("_job", "_spark"), how="outer", indicator=True
    )
    unmatched = int((merged["_merge"] != "both").sum())
    diffs = {
        index: float(np.nanmax(np.abs(merged[f"{index}_job"] - merged[f"{index}_spark"])))
        for index in ("ndvi", "ndmi")
    }
    valid_equal = bool((merged["valid_cells_job"] == merged["valid_cells_spark"]).all())
    # Months where every cell was masked are NaN on both sides: equal, not a mismatch.
    nan_agree = bool((merged["ndvi_job"].isna() == merged["ndvi_spark"].isna()).all())

    baseline, pandas_seconds = pandas_baseline(args.results_dir, meta)

    print(f"cell-month rows: {rows:,}  municipalities: {result[KEYS].drop_duplicates().shape[0]}")
    print(
        f"municipal-month rows: spark {len(result):,}  job {len(expected):,}  "
        f"pandas {len(baseline):,}"
    )
    print(
        f"parity vs job outputs: max |Δndvi| {diffs['ndvi']:.2e}  max |Δndmi| {diffs['ndmi']:.2e}  "
        f"valid_cells equal: {valid_equal}  missing months agree: {nan_agree}  "
        f"unmatched rows: {unmatched}"
    )
    for step, seconds in timings.items():
        print(f"spark  {step:<28} {seconds:6.1f} s")
    print(f"pandas per-municipality loop        {pandas_seconds:6.1f} s")


if __name__ == "__main__":
    main()
