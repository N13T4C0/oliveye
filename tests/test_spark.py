"""PySpark ETL must reproduce the pandas aggregation exactly (phase 2, ADR 0006)."""

import shutil

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from oliveye.pipeline.olive_grid import aggregate_cells

pyspark = pytest.importorskip("pyspark", reason="install the 'bigdata' extra to run Spark tests")
if shutil.which("java") is None:  # pragma: no cover - depends on the machine
    pytest.skip("Spark needs a Java runtime", allow_module_level=True)

from oliveye.spark.cells import aggregate_municipal, spark_session  # noqa: E402


@pytest.fixture(scope="module")
def spark():  # type: ignore[no-untyped-def]
    session = spark_session(app="oliveye-tests", master="local[2]")
    yield session
    session.stop()


def _cells() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "cell_id": ["a", "b", "c", "d"],
            "province_code": ["23", "23", "23", "18"],
            "municipality_code": ["60", "60", "60", "104"],
            "olive_ha": [6.0, 3.0, 1.0, 5.0],
        },
        geometry=[box(0, 0, 1, 1)] * 4,
        crs="EPSG:4326",
    )


def _tidy() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "month": ["2025-07"] * 4 + ["2025-08"] * 4,
            "cell_id": ["a", "b", "c", "d"] * 2,
            "ndvi": [0.30, 0.40, np.nan, 0.50, np.nan, np.nan, np.nan, 0.45],
            "ndmi": [-0.05, -0.02, 0.10, 0.00, np.nan, np.nan, np.nan, -0.01],
        }
    )


def test_spark_matches_pandas_weighted_means(spark) -> None:  # type: ignore[no-untyped-def]
    cells, tidy = _cells(), _tidy()
    expected = aggregate_cells(tidy, cells).sort_values(
        ["province_code", "municipality_code", "month"]
    )

    result = (
        aggregate_municipal(
            spark.createDataFrame(tidy.astype(object).where(tidy.notna(), None)),
            spark.createDataFrame(pd.DataFrame(cells.drop(columns="geometry"))),
        )
        .toPandas()
        .sort_values(["province_code", "municipality_code", "month"])
        .reset_index(drop=True)
    )

    assert list(result.columns) == list(expected.columns)
    pd.testing.assert_frame_equal(
        result.reset_index(drop=True), expected.reset_index(drop=True), check_dtype=False
    )


def test_masked_month_stays_missing(spark) -> None:  # type: ignore[no-untyped-def]
    """A month where every pixel was masked gives NaN and zero valid cells, never a value."""
    cells, tidy = _cells(), _tidy()
    result = aggregate_municipal(
        spark.createDataFrame(tidy.astype(object).where(tidy.notna(), None)),
        spark.createDataFrame(pd.DataFrame(cells.drop(columns="geometry"))),
    ).toPandas()
    martos_august = result[(result["municipality_code"] == "60") & (result["month"] == "2025-08")]
    assert martos_august["ndvi"].isna().all()
    assert martos_august["valid_cells"].tolist() == [0]


def test_literal_nan_is_missing_like_in_pandas(spark) -> None:  # type: ignore[no-untyped-def]
    """A NaN value (not a null) must be left out of the mean, as pandas does."""
    cells, tidy = _cells(), _tidy()
    expected = aggregate_cells(tidy, cells).sort_values(
        ["province_code", "municipality_code", "month"]
    )
    raw = spark.createDataFrame(
        [(r.month, r.cell_id, float(r.ndvi), float(r.ndmi)) for r in tidy.itertuples()],
        schema="month string, cell_id string, ndvi double, ndmi double",
    )
    result = (
        aggregate_municipal(
            raw, spark.createDataFrame(pd.DataFrame(cells.drop(columns="geometry")))
        )
        .toPandas()
        .sort_values(["province_code", "municipality_code", "month"])
    )
    pd.testing.assert_frame_equal(
        result.reset_index(drop=True), expected.reset_index(drop=True), check_dtype=False
    )
