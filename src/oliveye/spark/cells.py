"""Per-cell NDVI/NDMI series → municipal monthly means, with PySpark.

The openEO jobs return one row per 250 m olive cell and month (~9.5 million rows for the 86
municipalities, 2016-10 to 2026-09). This module does, at that scale, exactly what
`oliveye.pipeline.olive_grid.aggregate_cells` does in pandas for one municipality:

    mean index = Σ (index × olive ha) / Σ olive ha, over the cells with a valid value that month

Months where every pixel of a cell was masked (clouds) carry nulls (or NaN) and are left out of
the weighted mean; `valid_cells` says how many cells contributed, so thin months stay visible.

Spark concepts used (for readers new to it):
* a *DataFrame* is a distributed table; transformations are lazy and only run on an action
  (`count`, `write`, `toPandas`);
* `groupBy().agg()` aggregates in two stages (per partition, then merged), so it scales out;
* Parquet is a columnar file format: reading two columns of a wide table reads only those two.
"""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F  # noqa: N812 - the conventional alias
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

from oliveye.models.sources import INDEX_PERIODS

CELL_SCHEMA = StructType(
    [
        StructField("month", StringType(), nullable=False),
        StructField("cell_id", StringType(), nullable=False),
        StructField("ndvi", DoubleType(), nullable=True),
        StructField("ndmi", DoubleType(), nullable=True),
    ]
)
KEYS = ["province_code", "municipality_code"]


def spark_session(app: str = "oliveye", master: str = "local[*]") -> SparkSession:
    """Local Spark session; `local[*]` uses every core of this machine."""
    return (
        SparkSession.builder.appName(app)
        .master(master)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def read_cell_series(spark: SparkSession, results_dir: Path) -> DataFrame:
    """Every `indices_cells_*.csv` of every extraction period, with an explicit schema.

    An explicit schema avoids a full extra pass over 559 MB that schema inference would need.
    Periods cover disjoint months (see `oliveye.models.sources.INDEX_PERIODS`).
    """
    patterns = [
        str(results_dir / f"*-openeo-real-*-{period}" / "indices_cells_*.csv")
        for period in INDEX_PERIODS
        if any(results_dir.glob(f"*-openeo-real-*-{period}/indices_cells_*.csv"))
    ]
    return spark.read.csv(patterns, header=True, schema=CELL_SCHEMA)


def aggregate_municipal(cells: DataFrame, metadata: DataFrame) -> DataFrame:
    """Olive-hectare-weighted monthly means per municipality (same output as `aggregate_cells`).

    Args:
        cells: `month`, `cell_id`, `ndvi`, `ndmi` (nulls where the cell was masked).
        metadata: `cell_id`, `province_code`, `municipality_code`, `olive_ha` (one row per cell).
    """
    # Spark keeps a literal NaN as a number; pandas treats it as missing. Make NaN a null first,
    # so a NaN cell is left out of the mean (and of valid_cells) exactly as in pandas.
    clean = cells.select(
        "month",
        "cell_id",
        *[F.when(F.isnan(F.col(c)), None).otherwise(F.col(c)).alias(c) for c in ("ndvi", "ndmi")],
    )
    joined = clean.join(
        F.broadcast(metadata.select("cell_id", *KEYS, "olive_ha")), on="cell_id", how="inner"
    )

    def weighted(index: str) -> Column:
        valid = F.col(index).isNotNull()
        numerator = F.sum(F.when(valid, F.col(index) * F.col("olive_ha")))
        denominator = F.sum(F.when(valid, F.col("olive_ha")))
        return (numerator / denominator).alias(index)

    return (
        joined.groupBy("month", *KEYS)
        .agg(
            weighted("ndvi"),
            weighted("ndmi"),
            F.count(F.when(F.col("ndvi").isNotNull(), True)).alias("valid_cells"),
        )
        .select("month", *KEYS, "ndvi", "ndmi", "valid_cells")
    )


def write_parquet(frame: DataFrame, path: Path, partition_by: list[str] | None = None) -> None:
    """Overwrite `path` with the frame as Parquet (optionally partitioned, e.g. by province)."""
    writer = frame.write.mode("overwrite")
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.parquet(str(path))
