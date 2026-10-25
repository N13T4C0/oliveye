# ADR 0005 — Web and API deployed on Vercel, API serving pre-built JSON

- **Status:** accepted (author's choice: web + deployed API, Vercel)
- **Date:** 2026-10-25

## Context

Phase 5 needs a public product: a map of the measured olive area, monthly NDVI/NDMI series per
municipality, and production vs aforo vs model per province, with the dated 2026/27 forecast.
The data changes about once a year (a new campaign). The author wants the FastAPI backend to be
deployed too, not only a static site.

## Decision

1. **Two Vercel projects from this repo:** `web/` (Next.js, TypeScript strict, MapLibre) and
   `api/` (FastAPI as a Vercel Python function; Root Directory `api/`, entrypoint `api/app.py`).
2. **The API reads small pre-built JSON** (`api/data/`, ~1.8 MB in total), written by
   `scripts/export_api_data.py`. No pandas or geodata libraries at runtime: FastAPI only.
3. **`api/data/` is committed.** It is published, derived data from public sources, reviewed like
   `docs/results/`. Raw and interim data stay in `data/` and out of git (CLAUDE.md rule).
4. **Map geometry = the olive cells we measured**, dissolved per municipality and simplified
   (60 m) in EPSG:25830, stored in EPSG:4326 (`municipality_footprints`). No new boundary source.
5. **Caching:** every API response carries `s-maxage=86400, stale-while-revalidate`; the web
   fetches on the server with daily revalidation, so visitors rarely wait on Python.
6. **Names:** official INE names with accents (`docs/sources/ine_municipality_names.csv`, from
   the INE 2026 municipality dictionary), article moved to the front ("La Carolina").

## Alternatives considered

- *Static web with JSON only* (no deployed API): simpler and never cold, but the author wants the
  backend visible; the API stays the single data contract for the web.
- *Render / Fly for the API:* free tiers sleep (tens of seconds to wake) or need a card; Vercel
  runs FastAPI as functions behind its CDN, one account for both projects.
- *pandas in the API:* convenient, but a heavier bundle and slower cold starts for no benefit
  once the export does the work.

## Consequences

- After each model run: `scripts/export_api_data.py`, review, commit `api/data/`; Vercel redeploys.
- Interview line: "the export does the heavy lifting once; the API is a thin, cacheable contract,
  so a free serverless tier is enough."
