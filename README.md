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
Climate (ERA5 via Open-Meteo) ───────────────────────────────────────────────────────┼─► PostGIS
Historical production (Junta de Andalucía, AICA) ────────────────────────────────────┘
      ──► features per province & campaign ──► Baseline / Ridge / XGBoost (MLflow)
      ──► FastAPI ──► Next.js + MapLibre (map, time series, prediction vs aforo)
```

## Roadmap

| Phase | Goal | Main deliverables | Status |
|---|---|---|---|
| **0. Setup** | Project ready to work | Repo structure, `CLAUDE.md`, Docker + PostGIS, `pyproject.toml` | ✅ Done |
| **1. Exploration** | Understand the data | Notebooks: openEO NDVI time series for sample parcels, SIGPAC olive parcels, first look at production data | ✅ Done |
| **2. Data pipeline** | Reproducible ETL | SIGPAC → PostGIS, NDVI/NDMI per parcel/province via openEO batch jobs (cached), climate and production ingestion, PySpark aggregation | 🔄 Extraction done (86 municipalities); PostGIS + PySpark pending |
| **3. Models** | Honest prediction | Feature table per province & campaign; baseline, Ridge, XGBoost; leave-one-campaign-out; MLflow tracking; comparison with *aforo* | ✅ First version |
| **4. API** | Serve results | FastAPI endpoints (parcels, time series, predictions), tests, Docker image | 🔄 Read-only API with tests; not deployed |
| **5. Web & deploy** | Public product | Next.js + MapLibre map, NDVI/NDMI charts, prediction vs aforo; CI/CD with GitHub Actions; deployment | ⬜ |

## Results

**Question:** with satellite (Sentinel-2) and climate data up to August, can a simple model
forecast a province's olive oil harvest as well as the official forecast (*aforo*) published by
the Junta de Andalucía in October (which also uses field fruit counts)?

**Short answer:** not yet. With 9 campaigns the model reduces to the province average (44 %
MAPE, the same as repeating last year's harvest), while the aforo, which also counts fruit in the
field in October, has 12 %: about 3–4× lower and closer in 6 of 9 campaigns (suggestive, not
conclusive: p = 0.055).

| Model (same 15 rows, 9 campaigns) | MAPE | Median APE | Campaigns closer than the aforo |
|---|---|---|---|
| Aforo (Junta, October, field counts) | 11.9 % | 11.2 % | – |
| **OlivEye — Ridge, data to August** | 44.1 % | 30.7 % | 3 / 9 (p = 0.055) |
| Repeat last campaign | 44.0 % | 28.6 % | 1 / 9 |
| Province mean | 45.4 % | 30.6 % | 3 / 9 |

![Real production, aforo and OlivEye per campaign](docs/results/figures/production_vs_aforo.png)

### How it was validated

- **Leave-one-campaign-out:** each campaign (both provinces) is predicted by a model that never
  saw it, nor the following campaign, whose "last year's production" feature would reveal it.
- **Forward check:** training only on earlier campaigns gives 53.9 % MAPE vs 12.4 % for the
  aforo (5 campaigns, too few for inference).
- Ridge regression on 4 features fixed in advance (last year's production, May heat days,
  summer NDMI, spring NDVI), with the province level unpenalised (ADR 0003). The selected
  shrinkage removes the features: the model is, in practice, the province mean.
- 80 % interval: forecast ÷/× 2.0, from the 16 out-of-sample errors (coverage not validated).

### Limitations (read before quoting a number)

- Only 9 campaigns since Sentinel-2 (2015): every metric is noisy.
- 15 of 16 "real" production values are derived from the Junta's aforo variations (ADR 0002).
- Olive trees alternate heavy and light years; the aforo uses field fruit counts in October that
  a satellite cannot see in August.
- Granada lacks reliable figures for 2016/17 and 2017/18 (rows dropped, not imputed).
- Features cover 80.1 % of Jaén's and 80.6 % of Granada's SIGPAC olive area.

Full numbers, caveats and raw outputs: [`docs/results/`](docs/results/README.md).

## Current status

**October 2026: models done, web next.** 16 province-campaigns, features from 86 municipalities
(~80 % of each province's olive area) extracted on the server with openEO for 1,492 credits.
Decisions are recorded in [`docs/decisions/`](docs/decisions/) and next steps in
[`TODO.md`](TODO.md).

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
- **Climate** — ERA5 daily reanalysis via [Open-Meteo](https://open-meteo.com/) (RIA stations planned).
- **Production & aforo** — Junta de Andalucía, AICA.

## Repository structure

See [`CLAUDE.md`](CLAUDE.md#repository-layout).

## License

MIT for the code. Data remain under the licenses of their providers.
