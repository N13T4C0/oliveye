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
- [x] Catastro ↔ INE codes + names for 271 municipalities (`catastro_ine_mapping` job)
- [x] Aforo per province: yearly Junta PDFs "Estimacion_ACEITE_MESA_<campaign>"; parser `oliveye.pipeline.production` (2021/22–2026/27)
  - Derived previous-campaign finals match AICA (Andalucía 2023/24: 578,100 vs 580,464 t)
- [x] Aforo table 2021/22–2026/27 on the results branch (`aforo_by_province.csv`)
  - Junta aforo error in Jaén vs derived final: −21 % (2024/25) to +22 % (2025/26) → the bar to beat
- [x] Aforo 2016/17, 2019/20, 2020/21 from official press releases (`docs/sources/aforo_press_releases.csv`)
- [ ] Aforo 2015/16, 2017/18, 2018/19 (no PDF or release found yet)
- [x] Target variable decided (ADR 0002): Junta final production derived from aforo variations,
  validated vs AICA regional totals (−0.4 %, −0.2 %). Jaén: 8 campaigns, Granada: 7
- [x] Target gaps filled with cited sources: Jaén complete 2015/16–2025/26 (2018/19 = AICA 667,855 t,
  matches the derived value within 0.4 %); Granada 2018/19 from a published share, 2019/20 from the 2020/21 aforo
- [ ] Granada 2016/17 and 2017/18 still missing → those rows are dropped (ADR 0003 #16)
- [ ] Install uv and Docker; run `uv sync` (done on Windows) and `docker compose up -d`

## Automation (2026-10-24)
- [x] 9 subagents from agency-agents + `oliveye-auditor` in `.claude/agents/`
- [x] Skills in `.claude/skills/`: grill-me, find-skills, impeccable, web-design-guidelines, seo-audit, ai-seo
- [x] `DESIGN.md` (adapted from Wise on styles.refero.design)
- [x] Local folder on the author's PC is a git clone of the repo
- [x] Job queue on GitHub Actions (`jobs/` → `results` branch) + CI workflow
- [ ] **Author, once:** `uv run python scripts/export_openeo_refresh_token.py` (stores the openEO secret)
- [ ] Long term: client credentials + ask CDSE support to link them to the personal account

## Automation hardening (2026-10-24, autonomous block)
- [x] Parallel workers split by request; per-request credit logs; budget guard; safety-net publish
- [x] Orphaned paid jobs recovered from the openEO backend by title (2 incidents, 0 credits lost)
- [x] Skills: ponytail + 5 addyosmani agent-skills; graphify/OmniRoute evaluated and skipped

## Phase 3 groundwork
- [x] `oliveye.models.features`: seasonal NDVI/NDMI per campaign, data cut at August (aforo time)
- [x] Climate: Open-Meteo ERA5 daily weather for the 86 municipalities (30 ERA5 cells, 2016–2026)
- [ ] RIA stations: the web service returns an HTML page to GitHub runners (bot protection?) — retry later or from the author's PC
- [x] Feature table per province × campaign (`models/dataset.py`: indices + climate + lagged production)
- [x] Baselines (last campaign, 5-year mean, province mean, aforo) and Ridge with leave-one-campaign-out
- [x] `/grill-me` session with the author → ADR 0003 (17 decisions)
- [x] Implement `models/dataset.py`, `train.py`, `evaluate.py`, `scripts/train_models.py` (TDD)
  (rows: Jaén 2017/18–2025/26 = 9, Granada 2019/20–2025/26 = 7 → 16)
- [x] Statistician review → ADR 0003 amendment: t+1 held out with t (lag leak), `ProvinceAnomalyRidge`,
  1-SE alpha rule, like-for-like metrics, sign-flip test, conformal interval, forward check
- [x] Code review + oliveye-auditor on the model code (no leakage found; fixes applied)
- [x] Result figures (`models/plots.py`) + `04_model_results.ipynb`; local MLflow (`--extra tracking`)
- [x] FastAPI read-only service over the results (Phase 4 groundwork, not deployed)
- [x] XGBoost negative test documented (ADR 0004)
- [x] Final training on all 86 municipalities → `model-qa` + auditor → `docs/results/` (2026-10-25)
  - LOCO, 15 like-for-like rows / 9 campaigns: Ridge 44.1 %, last campaign 44.0 %, province mean 45.4 %,
    aforo 11.9 % (3.7×, CI 1.3–7.6×; aforo closer in 6/9, p = 0.055). The model reduces to the province mean.
  - Fixes from the reviews: target origin labelled (`target_method`), causal outlier filter, aforo timing
    (October, field counts), 2020/21 aforo source verified in the Junta PDF
- [ ] Ideas to make the model useful (next session, decide with the author): more campaigns via
  Landsat (pre-2015), municipal or comarca-level targets if a source exists, or reframe as
  "early signal in August" vs the October aforo
- [x] README headline approved by the author and published (2026-10-25)
- [x] Dated 2026/27 forecast published (`docs/results/forecast-2026-27.md`); score it in autumn 2027

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
- [x] openEO secret set; first paid run 2026-10-24: Martos, July 2025, 3,130 olive cells (85.9 % of its olive area,
  mean purity 95.7 %), **4 credits**, ~3 min. NDVI 0.271, NDMI −0.068 (summer water stress)
  - First attempt failed with HTTP 413 (3 MB outline, 0 credits) → switched to 250 m olive-dominant grid (ADR 0001 addendum)
- [x] Martos 2024/25 (12 months) = 6 credits; Martos 2016/17–2025/26 (120 months) = 23 credits, 16 min
  → one job per municipality with its whole history (cap 120 months)
- [x] 2016/17–2025/26 indices for the 86 municipalities with 80 % of the olive area
  (Jaén 48, Granada 38): finished 2026-10-25 04:13 UTC, 86 ok, 0 errors, **1,492 credits**
  (estimate was 560–810: Jaén municipalities are larger; budget 3,100); 80.1 % / 80.6 % of olive area
  - 25 fragmented municipalities (mostly Granada) have < 60 % coverage at 80 % purity (≥ 22 cells each)
- [x] Check the batch finished; nothing to re-queue (0 errors)
- [ ] Extrapolate cost to a full campaign and to all municipalities of Jaén + Granada
- [ ] `02_sigpac_olive_parcels.ipynb`: load SIGPAC, filter olive uses, areas per municipality/province, map
- [ ] `03_production_history.ipynb`: production and aforo per province and campaign since 2015
- [x] Decide the aggregation unit for Phase 2: olive area per municipality (ADR 0001)
- [x] Write ADR for the openEO strategy (`docs/decisions/0001-openeo-extraction-strategy.md`)
- [x] Fix ruff errors in notebook 01; CI now lints the whole repo (notebooks included)
- [x] Credits log working (`data/cache/openeo/credits_log.csv`); baseline 10,000 on 2026-10-22
