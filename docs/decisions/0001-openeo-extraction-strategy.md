# ADR 0001 — openEO extraction strategy

- **Status:** accepted
- **Date:** 2026-10-24

## Context

Sentinel-2 indices are extracted from the Copernicus Data Space Ecosystem (CDSE) through openEO,
which has a free allowance of 10,000 credits per month that does not roll over. Jaén and Granada
together have hundreds of thousands of olive parcels and the model needs ~10 campaigns of data.
Downloading raster cubes, or one time series per parcel, would not fit in the free tier and would
not be needed: production is published per province, not per parcel.

Notebook 01 (7 parcels x 2 years, one value per image) cost 5 credits and showed residual clouds
passing the SCL mask (e.g. NDVI ≈ 0.03 in December 2025).

## Decision

1. **Batch jobs, not synchronous requests.** One batch job per (area, period). Sync requests
   time out on large areas and are billed per call.
2. **Unit of aggregation: the olive area of each municipality.** All SIGPAC `OV` parcels of a
   municipality, shrunk by 10 m (one pixel) and dissolved into one geometry. Output size depends
   on the number of municipalities, not on the number of parcels, and municipalities can be
   summed into provinces weighted by area.
3. **Everything is reduced on the server**, in this order: SCL cloud mask → NDVI and NDMI per
   pixel → monthly median per pixel → spatial mean per geometry. Only a CSV of
   month x municipality x index is downloaded.
4. **Monthly median composites** instead of every image: the median removes most residual
   clouds, and monthly resolution is enough for a target that is yearly.
5. **Local outlier flag** (Hampel filter, rolling median ± 3 MAD) on the monthly series. Raw
   values are kept and flagged, never silently deleted.
6. **Cache key = SHA-256 of the canonical process graph** (collection, bands, extent, dates,
   geometries and every step). The cache is checked before contacting the backend, so a repeated
   request costs 0 credits. Credits per job are appended to `data/cache/openeo/credits_log.csv`.
7. **Measure before scaling:** run one month for one municipality (Martos), read the cost, then
   budget whole campaigns and provinces from that number.

## Alternatives considered

| Alternative | Why not |
|---|---|
| One series per parcel (notebook 01 approach) | Output and cost grow with parcel count; the target is per province anyway. |
| One geometry per province | Cheapest, but loses the municipality map for the web app and makes debugging harder. |
| Download cubes and process locally (xarray) | Many GB per campaign, slow, and defeats the purpose of server-side processing. |
| Google Earth Engine | Free for non-commercial use, but the project aims to showcase the European Copernicus stack and openEO is an open standard. |

## Consequences

- Within-municipality variability is lost; if needed later, a stratified sample of parcels can
  be added as a second, cheaper extraction.
- Dissolved geometries can be large; they are simplified to 5 m (half a pixel) to keep the
  request small. The dry-run mode of `scripts/extract_monthly_indices.py` prints the vertex count
  before any credit is spent.

## Addendum (2026-10-24): olive-dominant grid cells

First real run for Martos (Jaén) failed before any job was created: the dissolved outline of
~18,000 olive parcels was a 3 MB inline GeoJSON and CDSE answered **HTTP 413 Request Entity Too
Large** (0 credits spent). Simplifying the outline enough to fit 1 MB lost more than 25 % of the
measured olive area.

**Revised unit:** 250 m grid cells (EPSG:25830, edges on multiples of 250 m, hence on the 10 m
Sentinel-2 pixel grid) where SIGPAC olive parcels cover **≥ 80 %** of the cell
(`oliveye.pipeline.olive_grid`). Each cell is sent as its own feature; municipality values are
the olive-area-weighted mean of their cells.

- Payload: 5 vertices per cell, ~150 bytes; a municipality fits easily under 1 MB.
- Purity: cells are dominated by olive trees, so roads, villages and cereal fields at parcel
  edges no longer dilute the signal (it replaces the 10 m inner buffer).
- Coverage is reported per run (`coverage_pct`: share of the municipality's olive area inside
  kept cells); the threshold is a parameter if a municipality is too fragmented.
- Bonus: per-cell series feed the web map directly.
