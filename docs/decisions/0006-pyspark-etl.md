# ADR 0006 — PySpark for the per-cell ETL, with pandas parity

- **Status:** accepted
- **Date:** 2026-10-25

## Context

The openEO jobs return one row per 250 m olive cell and month: **9,481,800 rows** (559 MB of CSV)
for the 86 municipalities, October 2016 to September 2026. Until now each municipality was
aggregated with pandas inside its own job (`olive_grid.aggregate_cells`). Phase 2 of the plan
(and the author's course) calls for a reproducible Big Data ETL with PySpark.

## Decision

1. `oliveye.spark.cells` (optional extra `bigdata`) reads all per-cell CSVs with an explicit schema,
   joins the cell metadata (province, municipality, olive hectares) as a broadcast table, and writes:
   - `data/interim/cells.parquet` — every cell-month, partitioned by province (146 MB, 3.8× smaller);
   - `data/processed/municipal_monthly.parquet` — olive-hectare-weighted monthly NDVI/NDMI.
2. **Parity is a test, not a hope.** The Spark aggregation must equal pandas `aggregate_cells`:
   a unit test on synthetic data (including fully cloud-masked months) and a full-data check in
   `scripts/spark_aggregate.py` against the 86 job outputs.
3. The modelling code keeps reading the per-municipality outputs; Spark is the scalable path for
   new or larger extractions (all of Andalusia, parcel level), not a rewrite of what works.

## Evidence (2026-10-25, 2 cores, 7 GB RAM, Spark 4.2 local mode)

| Step | Time |
|---|---|
| Spark: 559 MB CSV → partitioned Parquet | 17.4 s |
| Spark: Parquet → 10,320 municipal-month rows | 4.0 s |
| pandas: per-municipality loop over the CSVs | 13.6 s |

Parity on the full data: max |Δ NDVI| 3.0·10⁻¹⁵, max |Δ NDMI| 7.1·10⁻¹⁶ (floating-point rounding),
`valid_cells` identical, cloud-masked months missing on both sides, 0 unmatched rows.

## Why, and what it does not claim

- At this size, on two cores, Spark is **not faster** than pandas: the data fits in memory and Spark
  pays for its JVM start and planning. That is the honest result.
- What Spark buys: columnar Parquet that re-aggregates in 4 s without re-reading CSV, partitioning
  by province, lazy plans that run unchanged on a cluster, and a path to 10–100× more rows (every
  olive municipality of Andalusia, or parcel-level series) without changing the code.
- Interview line: "I added Spark where the data shape justified it, proved it matches pandas to
  1e-15, and measured that at today's size pandas is just as fast — so the model keeps the simple path."
