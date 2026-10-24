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
- [x] SIGPAC subset fetcher (`scripts/fetch_sigpac_subset.py`, DuckDB over remote GeoParquet)
- [x] Download sample municipality: Martos (23/60) — 21,401 OV parcels (21,796 ha), 477 TA (104 ha)
- [ ] Download SIGPAC for all of Jaén (23) and Granada (18) (Phase 2)
- [ ] Investigate municipality code `900` in the Jaén ranking (24,113 ha OV) before summing provinces
- [x] Aforo per province: yearly Junta PDFs "Estimacion_ACEITE_MESA_<campaign>" (5 found, download queued)
- [ ] Actual production per province: find AICA provincial series (reports only give % per province)
- [ ] Install uv and Docker; run `uv sync` (done on Windows) and `docker compose up -d`

## Automation (2026-10-24)
- [x] 7 subagents from agency-agents in `.claude/agents/`
- [x] Job queue on GitHub Actions (`jobs/` → `results` branch) + CI workflow
- [ ] **Author, once:** `uv run python scripts/export_openeo_refresh_token.py` (stores the openEO secret)
- [ ] Long term: client credentials + ask CDSE support to link them to the personal account

## Phase 1 — Exploration
- [x] `01_openeo_ndvi_sample_parcels.ipynb` + `oliveye.pipeline.openeo_ndvi` written and dry-run tested
- [x] Run notebook 01 against CDSE (2026-10-23): 1 batch job, 7 parcels x 2 years = **5 credits**
  - Olive NDVI is seasonal (~0.48 winter / ~0.27 late summer): canopy + understory mix
  - TA parcels in Martos are a weak cereal control (2 small parcels, different behaviour)
  - Residual clouds pass the SCL mask (e.g. Dec 2025 NDVI ≈ 0.03)
- [ ] Add a proper cereal control: TA parcels from a campiña municipality
- [x] Monthly median NDVI + NDMI composites on the server, per municipality olive area
  (`oliveye.pipeline.openeo_indices`, `scripts/extract_monthly_indices.py`) + Hampel outlier flag
- [ ] **Before 2026-11-01** (credits expire): dry run (queued as a job), then 1 real month of Martos and log the cost
- [ ] Extrapolate cost to a full campaign and to all municipalities of Jaén + Granada
- [ ] `02_sigpac_olive_parcels.ipynb`: load SIGPAC, filter olive uses, areas per municipality/province, map
- [ ] `03_production_history.ipynb`: production and aforo per province and campaign since 2015
- [x] Decide the aggregation unit for Phase 2: olive area per municipality (ADR 0001)
- [x] Write ADR for the openEO strategy (`docs/decisions/0001-openeo-extraction-strategy.md`)
- [ ] Fix ruff errors in notebook 01 (`uv run ruff check .` fails on it)
- [x] Credits log working (`data/cache/openeo/credits_log.csv`); baseline 10,000 on 2026-10-22
