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
- [x] Code `900` = Jaén capital (Catastro numbering: SIGPAC municipality codes are **Catastro codes, not INE**; 900 = provincial capital). Bounds around Jaén city; 24,113 ha OV. Not a duplicate.
- [x] SIGPAC OV vs Junta yearbook: Jaén 584,828 / 588,818 ha (99.3 %), Granada 203,994 / 208,835 ha (97.7 %)
- [ ] Map Catastro municipality codes to INE codes and names before joining other sources
- [x] Aforo per province: yearly Junta PDFs "Estimacion_ACEITE_MESA_<campaign>"; parser `oliveye.pipeline.production` (2021/22–2026/27)
  - Derived previous-campaign finals match AICA (Andalucía 2023/24: 578,100 vs 580,464 t)
- [x] Aforo table 2021/22–2026/27 on the results branch (`aforo_by_province.csv`)
  - Junta aforo error in Jaén vs derived final: −21 % (2024/25) to +22 % (2025/26) → the bar to beat
- [ ] Find aforo PDFs for 2015/16–2020/21
- [ ] Actual production per province: find AICA provincial series (reports only give % per province)
- [ ] Install uv and Docker; run `uv sync` (done on Windows) and `docker compose up -d`

## Automation (2026-10-24)
- [x] 9 subagents from agency-agents + `oliveye-auditor` in `.claude/agents/`
- [x] Skills in `.claude/skills/`: grill-me, find-skills, impeccable, web-design-guidelines, seo-audit, ai-seo
- [x] `DESIGN.md` (adapted from Wise on styles.refero.design)
- [x] Local folder on the author's PC is a git clone of the repo
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
- [x] Dry run Martos 1 month: 1 geometry, 14,307 ha measured (of 21,618), bbox 553 km², 135k vertices
- [ ] **Before 2026-11-01** (credits expire): 1 real month of Martos (needs the openEO secret) and log the cost
- [ ] Extrapolate cost to a full campaign and to all municipalities of Jaén + Granada
- [ ] `02_sigpac_olive_parcels.ipynb`: load SIGPAC, filter olive uses, areas per municipality/province, map
- [ ] `03_production_history.ipynb`: production and aforo per province and campaign since 2015
- [x] Decide the aggregation unit for Phase 2: olive area per municipality (ADR 0001)
- [x] Write ADR for the openEO strategy (`docs/decisions/0001-openeo-extraction-strategy.md`)
- [ ] Fix ruff errors in notebook 01 (`uv run ruff check .` fails on it)
- [x] Credits log working (`data/cache/openeo/credits_log.csv`); baseline 10,000 on 2026-10-22
