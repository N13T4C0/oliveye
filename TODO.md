# TODO

Updated at the end of each phase.

## ✅ Phase 0 — Setup (done)
- [x] Repository structure
- [x] `CLAUDE.md` with conventions and Copernicus quota rules
- [x] `docker-compose.yml` (PostgreSQL 17 + PostGIS 3.5)
- [x] `pyproject.toml` with Phase 1 dependencies
- [x] Initial `README.md` and roadmap

## 🔜 Before Phase 1 (manual, outside the code)
- [x] Create GitHub repo `oliveye` and push the initial commit
- [x] Create Copernicus Data Space Ecosystem account and log in to openEO once (2026-10-22, refresh token OK)
- [x] Check monthly openEO credit balance (2026-10-22: 10,000 CDSE + 5,000 Terrascope; current allowance expires 2026-11-01 06:00)
- [ ] Download SIGPAC for Jaén (23) and Granada (18) into `data/raw/sigpac/` (one olive municipality is enough to start notebook 01)
- [ ] Locate historical production / aforo data (Junta de Andalucía, AICA) — just bookmark sources
- [ ] Install uv and Docker; run `uv sync` (done on Windows) and `docker compose up -d`

## Phase 1 — Exploration
- [ ] `01_openeo_ndvi_sample_parcels.ipynb`: NDVI time series (2 years) for 3–5 olive parcels, cloud-masked, aggregated remotely, cached
- [ ] `02_sigpac_olive_parcels.ipynb`: load SIGPAC, filter olive uses, areas per municipality/province, map
- [ ] `03_production_history.ipynb`: production and aforo per province and campaign since 2015
- [ ] Decide the aggregation unit for Phase 2 (parcel sample vs municipality vs province)
- [ ] Write `docs/decisions/` ADR for the openEO strategy (sync vs batch, cache key)
- [ ] Start `data/cache/openeo/credits_log.csv` with the baseline balance (10,000 on 2026-10-22)
