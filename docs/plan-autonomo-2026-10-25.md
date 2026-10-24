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
- [ ] G. Phase 4 groundwork: FastAPI read-only service over the results (municipalities, monthly
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
