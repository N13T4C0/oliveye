"""Monthly series from several extraction periods must join into one continuous series."""

from pathlib import Path

import pandas as pd

from oliveye.models.sources import INDEX_PERIODS, index_series_paths, load_monthly


def _write(results: Path, job: str, months: list[str], ndvi: list[float]) -> None:
    folder = results / job
    folder.mkdir(parents=True)
    pd.DataFrame(
        {
            "month": months,
            "province_code": "23",
            "municipality_code": "60",
            "ndvi": ndvi,
            "ndmi": [0.0] * len(months),
            "valid_cells": [100] * len(months),
            "ndvi_outlier": [False] * len(months),  # stale centred flags: must be recomputed
        }
    ).to_csv(folder / "indices_monthly_23_60.csv", index=False)


def test_periods_join_without_gaps_or_duplicates(tmp_path: Path) -> None:
    _write(tmp_path, "2026-10-26-openeo-real-23-60-2015-2016", ["2016-08", "2016-09"], [0.3, 0.31])
    _write(tmp_path, "2026-10-24-openeo-real-23-60-2016-2026", ["2016-10", "2016-11"], [0.4, 0.41])
    # A one-off test extraction for a single month must never leak into the model inputs.
    _write(tmp_path, "2026-10-24-openeo-real-23-60-2025-07", ["2016-10"], [0.9])

    monthly = load_monthly(tmp_path)

    assert [str(m) for m in monthly["month"]] == ["2016-08", "2016-09", "2016-10", "2016-11"]
    assert monthly["ndvi"].tolist() == [0.3, 0.31, 0.4, 0.41]
    assert {"ndvi_outlier", "ndvi_clean"} <= set(monthly.columns)


def test_overlapping_months_keep_the_main_extraction(tmp_path: Path) -> None:
    _write(tmp_path, "2026-10-26-openeo-real-23-60-2015-2016", ["2016-09", "2016-10"], [0.3, 0.1])
    _write(tmp_path, "2026-10-24-openeo-real-23-60-2016-2026", ["2016-10", "2016-11"], [0.4, 0.41])

    monthly = load_monthly(tmp_path)

    assert monthly.loc[monthly["month"] == pd.Period("2016-10", "M"), "ndvi"].tolist() == [0.4]


def test_only_known_periods_are_read(tmp_path: Path) -> None:
    _write(tmp_path, "2026-10-24-openeo-real-23-60-2024-25", ["2024-10"], [0.5])
    assert index_series_paths(tmp_path, "indices_monthly_*.csv") == []
    assert INDEX_PERIODS[-1] == "2016-2026"
