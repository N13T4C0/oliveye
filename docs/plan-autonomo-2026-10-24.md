# Autonomous work block — 2026-10-24, 18:00–21:00 (Europe/Madrid)

The author is away. The assistant works alone through the job queue (GitHub Actions) and this
repo. Each check-in reads this file, advances the next open step and logs progress below.

## Guard rails

- openEO budget for this block: **≤ 3,000 credits** (≈ 9,990 left, expiring 2026-11-01).
- `oliveye-auditor` before every paid batch; dry runs reviewed before real runs.
- Nothing irreversible outside the repo; no deletions on the author's PC.
- Commits as Nieto, Conventional Commits, no AI trailers.

## Steps

1. [x] Validate cost of Martos 2016/17–2025/26 in one job (`2026-10-24-openeo-real-23-60-2016-2026`).
2. [x] Dry runs for municipalities covering 80 % of olive area (Jaén 48, Granada 38) → review
       cells, coverage, payload.
3. [ ] Auditor → real runs for the same municipalities (largest first, stop at the budget).
4. [ ] Aforo PDFs 2015/16–2020/21 (find URLs, `aforo_table` job).
5. [x] AICA actual production per province and campaign (find a primary source).
6. [ ] Catastro → INE municipality code mapping (names for the map, joins with climate).
7. [x] Evaluate ponytail, omniroute, graphify, addyosmani agent-skills; install what helps.
8. [ ] Wrap-up: TODO (repo + project), sync the author's folder, summary message.

## Log
- 18:05 Plan written; 5 check-ins scheduled (every ~35 min until ~21:00).
- 18:07 Queued 85 dry runs (Jaén 47 + Granada 38, 80 % of olive area). Martos 120-month real job running.
- 18:10 Step 7 done: installed ponytail + 5 addyosmani skills; graphify and OmniRoute left out (README).
- 18:13 Step 4 partial: aforo 2016/17, 2019/20, 2020/21 curated from official press releases
  (`docs/sources/aforo_press_releases.csv`); 2015/16, 2017/18, 2018/19 still missing.
- 18:15 Step 6 started: `sigpac_schema` job + INE municipality dictionary download queued.
- 18:18 Step 5: no open AICA provincial series; ADR 0002 sets the target to the Junta final
  production derived from aforo variations (validated vs AICA: −0.4 %, −0.2 %). Gaps: 2016/17–2017/18, 2019/20.
- 18:20 Target series built (`final_production_series`): Jaén 8 campaigns (2015/16, 2018/19,
  2020/21–2025/26), Granada 7. With satellite data from 2016/17, Jaén has 7 usable campaigns.
- 18:20 Martos 120-month job queued then running on openEO; dry runs queued behind it.
- 18:22 Step 1 done: Martos 2016/17–2025/26 in one job = **23 credits, 16 min**. Credits are
  fine (~85 × ≤23 ≈ 2,000), time is the bottleneck (~22 h serial) → two parallel workers.
- 18:27 Two-worker queue audited (NEEDS WORK → fixed: split by request, legacy log on resume,
  clean rebase abort, single re-dispatcher) and pushed without job files.
- 18:27 Dry runs progressing on the old single-worker run (14/86).
- 18:33 Step 2 done: 86/86 dry runs ok, all payloads < 1 MB (max 814 KB), median coverage 71 %;
  25 fragmented municipalities (mostly Granada) below 60 % coverage but ≥ 22 pure cells each.
- 18:35 Credit budget guard added (OPENEO_CREDIT_BUDGET=3100 in the workflow).
- 18:37 Step 3 started: auditor PASS → 85 real jobs pushed (estimated 560–810 credits),
  two parallel workers.
- 18:41 Step 6: SIGPAC uses Catastro codes (Jaén 6 differ from INE, Granada 40). Added
  `catastro_ine_mapping` job (Catastro ConsultaMunicipio gives both codes + name); queued.
  Workers now re-read jobs/ from main before each job (applies to future runs).
- 18:42 Check-in 1 (fired 18:39). Log times above corrected: earlier entries were estimated
  and ran ahead of the real clock. Waiting for the first parallel openEO results.
- 18:55 Phase 3 groundwork: `oliveye.models.features` (seasonal NDVI/NDMI per campaign, data cut
  at August so it is comparable with the aforo; province = olive-area-weighted mean).
  Exploratory look at Martos vs Jaén production: 2022/23 (180 kt, heat wave during flowering)
  has normal spring NDVI → satellite alone misses flowering failure; 2023/24 shows the lowest
  summer NDMI (−0.106). Climate (heat in May) and alternate bearing (lagged production) needed.
9. [ ] NEW: climate source (RIA, Junta's agroclimatic network) → job type for daily data.
- 19:10 INCIDENT: both parallel workers failed with exit 126 (publish script without exec bit).
  Up to 4 paid openEO jobs finished without their results/credits being published.
- 19:25 Fix (audited twice): call the script with bash + exec bit; recover orphaned jobs from the
  openEO backend by title before creating new ones (fails closed). Queue restarted. Expected
  recovered at 0 extra cost.
- 19:00 Step 9 groundwork: `oliveye.pipeline.climate` + `ria_stations`/`ria_daily` jobs (RIA web
  service); stations job queued.
