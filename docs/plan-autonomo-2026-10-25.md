# Autonomous night block — 2026-10-24 21:40 → 2026-10-25 ~07:25 (Europe/Madrid, after the DST change)

The author is asleep. Work follows ADR 0003. Anything that needs the author's confirmation is
parked in "Pending for the author" and the work moves on.

## Guard rails

- No openEO spending outside the approved 85-municipality batch; hard budget 3,100 credits.
- `oliveye-auditor` before queue/pipeline changes; `model-qa` + auditor before any metric is
  written to `docs/results/`. Nothing goes to the README without the author.
- Commits as Nieto, Conventional Commits, no AI trailers. Nothing irreversible on the author's PC.

## Blocks

- [x] A. Model code with TDD: `models/dataset.py`, `train.py`, `evaluate.py`,
      `scripts/train_models.py`; `statistician` review of the validation; `code-reviewer`.
- [ ] B. Watch the openEO batch (progress, re-dispatch, budget, failed jobs).
- [ ] C. First real training on the municipalities available; MLflow local; `docs/results/`;
      notebook 04 (dataviz); `model-qa` + auditor review.
- [ ] D. Extras: XGBoost negative test + ADR 0004; Granada 2016/17–2017/18 gaps; RIA retry.
- [ ] F. When the batch finishes: final training with all 85 municipalities; refresh results,
      notebook 04; `model-qa` + auditor again.
- [x] G. Phase 4 groundwork: FastAPI read-only service over the results (municipalities, monthly
      series, province predictions) with tests; no deployment.
- [~] H. README results section as a **draft** (`docs/results/README-draft.md`) for the author.
- [ ] E. Wrap-up (~07:25): TODO (repo + project), sync the author's folder, morning summary.

## If the assistant stops (usage limits, errors)

- The GitHub Actions queue does not depend on this session: it keeps processing the batch,
  re-dispatches itself and stops at the 3,100-credit budget.
- Work is committed in small steps and this log is updated after each one, so an interruption
  leaves a clean, documented state; the next scheduled check-in (or a new session) resumes from
  this file and `TODO.md`.

## Pending for the author

- Results headline in the README (after reviewing `docs/results/`).
- Publishing the dated 2026/27 forecast.

## Log
- 21:45 Block A: TDD — 10 model tests written first (RED), then dataset/train/evaluate (GREEN);
  includes a leakage test that corrupts held-out targets. 98 tests pass.
- 21:50 First end-to-end run on provisional data (Jaén = Martos only, 3.7 % of its olive area;
  Granada 58.5 %): pipeline works; Ridge blows up on extreme campaigns (alpha 0.1 picked,
  Jaén 2023/24 predicted 2.4 Mt). Not published; waiting for the statistician review and for
  the batch. Aforo MAPE on these rows: 11.9 %.
- 22:05 Block G done (early, independent): FastAPI read-only service (`oliveye.api.app`) with 6
  tests written first, `scripts/export_api_data.py`, `api/README.md`. Verified on real data
  (Martos 120 months, production vs aforo, names from the Catastro table). 104 tests pass.
- 22:05 Batch: 22/85 municipalities, 408 credits; ~10/h → expected to finish around 04:30.
- 22:20 Check-in 1 (fired 22:17). Batch 27/85, 466 credits, 0 errors. The link to the author's PC
  dropped (computer probably asleep): the local-folder sync is parked until it reconnects.
- 22:25 Block D (part): ADR 0004 + `scripts/experiment_xgboost.py`; provisional XGBoost MAPE 84 %
  vs 43 % for "repeat last campaign" → documented negative result, to refresh with full data.
- 22:30 Granada 2016/17–2017/18: no reliable figure found (2018/19 release gives +57 % but no
  tonnage); rows stay dropped per ADR 0003 #16. Parked.
- 23:00 Check-in 2. The first statistician run had been killed by the 21:42 interruption; rerun.
  Findings: (1) LEAKAGE — when campaign t is held out, t+1 stays in training and its lag feature
  is t's real production → exclude t+1 from training (outer and inner folds); the current test
  does not catch it; (2) NDMI confounded with province → within-province centering inside the
  pipeline, clip test features to the training range, wider alpha grid with the 1-SE rule;
  (3) like-for-like rows for MAPE, per-campaign metrics, exact sign-flip test vs aforo;
  (4) conformal-style symmetric interval; (5) extra references (province mean, lag+province).
  Implementing all with tests first; ADR 0003 amended with a dated note.
- 23:15 Statistician amendments implemented with TDD (9 new tests written first, all RED, then
  GREEN). While running them on provisional data a design flaw appeared: the province indicator
  was shrunk by Ridge (both provinces pulled to a pooled mean, MAPE 80.8 %). Fixed with
  `ProvinceAnomalyRidge` (province level unpenalised; 2 more tests), a change driven by
  the provisional LOCO results and labelled as such in ADR 0003. Provisional run, leave-one-campaign-out
  (Jaén = 3.7 % of its olive area): Ridge 44.9 %, province mean 45.4 %, last campaign 44.0 %, aforo 11.9 %
  (9 campaigns, same 15 rows). Satellite/climate add nothing yet; not published. ADR 0003
  amended. 113 tests pass.
- 23:15 Batch: reported as stalled at 28/85 — **wrong**: the local results worktree was not
  updating `origin/results` (fetch without an explicit refspec). Corrected at 23:32.
- 23:28 Code review (approve with 2 fixes) and oliveye-auditor (no leakage; doc honesty fixes)
  applied: alpha guard for < 2 inner folds, unseen province is an error, 13a labelled as
  result-driven, forward check documents its inner alpha choice, XGBoost experiment scored with
  the same like-for-like summary. 115 tests pass.
- 23:32 Batch (fetched with `git fetch origin results:refs/remotes/origin/results`): 38/85
  municipalities, ~570 credits in the per-request logs, 0 errors; both workers running.
  Lesson recorded in docs/automation.md.
- 23:36 The new "unseen province is an error" guard caught a real case: inner forward folds where
  Granada (history from 2019/20) had no training rows; before, it was silently filled with a
  pooled mean. Splits now never score a province without training rows (test first). Rerun with
  38 municipalities (Granada 77.9 % of its olive area, Jaén 5.0 %; the batch does Granada first):
  LOCO Ridge 44.6 %, province mean 45.4 %, aforo 11.9 % — unchanged in substance. Not published.
- 23:40 Block C (part): local MLflow tracking (`uv sync --extra tracking`, MLflow 3.17, SQLite
  store + artifacts under data/mlflow/, git-ignored); verified with a real run. Batch 42/85,
  0 errors, expected to finish around 04:00.
- 00:20 Check-in 4. Batch 45/85 (Jaén started: 7), 0 errors. Verified the queue's time
  handling: a worker stops taking new jobs after 3 h and ends in success, so `continue`
  re-dispatches (no action needed). Block H: skeleton of `docs/results/README-draft.md` with
  placeholders only (no numbers until the full run is reviewed).
- 00:58 Check-in 5. Batch 48/85 (Jaén 10), 0 errors. Only worker 0 is publishing: worker 1 has
  been on one openEO job since ~23:22 (likely queued at CDSE; the 150-min job timeout ends it by
  ~01:52 at worst). Throughput ~5/h until the next generation re-dispatches both workers
  (~02:20); full data now expected around 05:30–06:30.
