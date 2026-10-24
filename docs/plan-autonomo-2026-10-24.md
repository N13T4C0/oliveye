# Autonomous work block — 2026-10-24, 18:00–21:00 (Europe/Madrid)

The author is away. The assistant works alone through the job queue (GitHub Actions) and this
repo. Each check-in reads this file, advances the next open step and logs progress below.

## Guard rails

- openEO budget for this block: **≤ 3,000 credits** (≈ 9,990 left, expiring 2026-11-01).
- `oliveye-auditor` before every paid batch; dry runs reviewed before real runs.
- Nothing irreversible outside the repo; no deletions on the author's PC.
- Commits as Nieto, Conventional Commits, no AI trailers.

## Steps

1. [ ] Validate cost of Martos 2016/17–2025/26 in one job (`2026-10-24-openeo-real-23-60-2016-2026`).
2. [ ] Dry runs for municipalities covering 80 % of olive area (Jaén 48, Granada 38) → review
       cells, coverage, payload.
3. [ ] Auditor → real runs for the same municipalities (largest first, stop at the budget).
4. [ ] Aforo PDFs 2015/16–2020/21 (find URLs, `aforo_table` job).
5. [x] AICA actual production per province and campaign (find a primary source).
6. [ ] Catastro → INE municipality code mapping (names for the map, joins with climate).
7. [x] Evaluate ponytail, omniroute, graphify, addyosmani agent-skills; install what helps.
8. [ ] Wrap-up: TODO (repo + project), sync the author's folder, summary message.

## Log
- 18:05 Plan written; 5 check-ins scheduled (every ~35 min until ~21:00).
- 18:10 Queued 85 dry runs (Jaén 47 + Granada 38, 80 % of olive area). Martos 120-month real job running.
- 18:15 Step 7 done: installed ponytail + 5 addyosmani skills; graphify and OmniRoute left out (README).
- 18:25 Step 4 partial: aforo 2016/17, 2019/20, 2020/21 curated from official press releases
  (`docs/sources/aforo_press_releases.csv`); 2015/16, 2017/18, 2018/19 still missing.
- 18:30 Step 6 started: `sigpac_schema` job + INE municipality dictionary download queued.
- 18:40 Step 5: no open AICA provincial series; ADR 0002 sets the target to the Junta final
  production derived from aforo variations (validated vs AICA: −0.4 %, −0.2 %). Gaps: 2016/17–2017/18, 2019/20.
- 18:50 Target series built (`final_production_series`): Jaén 8 campaigns (2015/16, 2018/19,
  2020/21–2025/26), Granada 7. With satellite data from 2016/17, Jaén has 7 usable campaigns.
- 18:50 Martos 120-month job still running on openEO (~55 min); dry runs queued behind it.
