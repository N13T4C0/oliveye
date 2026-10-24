# Autonomous night block — 2026-10-24 21:40 → 2026-10-25 ~07:25 (Europe/Madrid, after the DST change)

The author is asleep. Work follows ADR 0003. Anything that needs the author's confirmation is
parked in "Pending for the author" and the work moves on.

## Guard rails

- No openEO spending outside the approved 85-municipality batch; hard budget 3,100 credits.
- `oliveye-auditor` before queue/pipeline changes; `model-qa` + auditor before any metric is
  written to `docs/results/`. Nothing goes to the README without the author.
- Commits as Nieto, Conventional Commits, no AI trailers. Nothing irreversible on the author's PC.

## Blocks

- [ ] A. Model code with TDD: `models/dataset.py`, `train.py`, `evaluate.py`,
      `scripts/train_models.py`; `statistician` review of the validation; `code-reviewer`.
- [ ] B. Watch the openEO batch (progress, re-dispatch, budget, failed jobs).
- [ ] C. First real training on the municipalities available; MLflow local; `docs/results/`;
      notebook 04 (dataviz); `model-qa` + auditor review.
- [ ] D. Extras: XGBoost negative test + ADR 0004; Granada 2016/17–2017/18 gaps; RIA retry.
- [ ] F. When the batch finishes: final training with all 85 municipalities; refresh results,
      notebook 04; `model-qa` + auditor again.
- [x] G. Phase 4 groundwork: FastAPI read-only service over the results (municipalities, monthly
      series, province predictions) with tests; no deployment.
- [ ] H. README results section as a **draft** (`docs/results/README-draft.md`) for the author.
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
