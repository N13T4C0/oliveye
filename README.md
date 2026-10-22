# OlivEye 🫒🛰️

**Estimating olive oil production in Andalusia from space.**

OlivEye estimates the olive oil production of each campaign for the provinces of **Jaén** and
**Granada** using Sentinel-2 satellite imagery over the olive groves registered in SIGPAC, climate
data and historical production, and compares the estimate against the official harvest forecast
(*aforo*) published by the Junta de Andalucía.

> Portfolio project. The goal is not to beat the official forecast, but to build an honest,
> reproducible, end-to-end data product: from raw satellite data to a deployed interactive map.

## Why it's interesting

- Jaén alone produces a large share of the world's olive oil, and the harvest varies a lot from
  year to year (alternate bearing, drought). Early estimates matter for prices and planning.
- Olive groves are evergreen: their vegetation signal is subtle, which makes the remote-sensing
  side of the problem genuinely non-trivial.
- Only ~10 campaigns exist since Sentinel-2 started (2015), so the project focuses on **honest
  validation** (leave-one-campaign-out) and simple, explainable models.

## Architecture

```
SIGPAC olive parcels ──► Sentinel-2 NDVI/NDMI via openEO (aggregated in the cloud) ──┐
Climate (RIA / AEMET) ───────────────────────────────────────────────────────────────┼─► PostGIS
Historical production (Junta de Andalucía, AICA) ────────────────────────────────────┘
      ──► features per province & campaign ──► Baseline / Ridge / XGBoost (MLflow)
      ──► FastAPI ──► Next.js + MapLibre (map, time series, prediction vs aforo)
```

## Roadmap

| Phase | Goal | Main deliverables | Status |
|---|---|---|---|
| **0. Setup** | Project ready to work | Repo structure, `CLAUDE.md`, Docker + PostGIS, `pyproject.toml` | ✅ Done |
| **1. Exploration** | Understand the data | Notebooks: openEO NDVI time series for sample parcels, SIGPAC olive parcels, first look at production data | ⏳ Next |
| **2. Data pipeline** | Reproducible ETL | SIGPAC → PostGIS, NDVI/NDMI per parcel/province via openEO batch jobs (cached), climate and production ingestion, PySpark aggregation | ⬜ |
| **3. Models** | Honest prediction | Feature table per province & campaign; baseline, Ridge, XGBoost; leave-one-campaign-out; MLflow tracking; comparison with *aforo* | ⬜ |
| **4. API** | Serve results | FastAPI endpoints (parcels, time series, predictions), tests, Docker image | ⬜ |
| **5. Web & deploy** | Public product | Next.js + MapLibre map, NDVI/NDMI charts, prediction vs aforo; CI/CD with GitHub Actions; deployment | ⬜ |

## Current status

**Phase 0 completed (October 2026).** The repository skeleton, local PostGIS database and Python
environment are ready. No pipeline or model code yet. See [`TODO.md`](TODO.md) for next steps.

## Quickstart

Requirements: [uv](https://docs.astral.sh/uv/), Docker, a free
[Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/) account.

```bash
git clone <repo-url> oliveye && cd oliveye
uv sync                       # Python environment
cp .env.example .env          # set POSTGRES_PASSWORD
docker compose up -d          # PostgreSQL + PostGIS
uv run jupyter lab
```

## Data sources

- **Sentinel-2 L2A** — Copernicus Data Space Ecosystem, via openEO.
- **SIGPAC** — agricultural parcel registry (FEGA / Junta de Andalucía).
- **Climate** — RIA (Red de Información Agroclimática de Andalucía) and AEMET.
- **Production & aforo** — Junta de Andalucía, AICA.

## Repository structure

See [`CLAUDE.md`](CLAUDE.md#repository-layout).

## License

MIT for the code. Data remain under the licenses of their providers.
