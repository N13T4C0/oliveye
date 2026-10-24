# Autonomous night block — 2026-10-24 21:40 → 2026-10-25 ~03:30 (Europe/Madrid)

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
- [ ] E. Wrap-up: TODO (repo + project), sync the author's folder, morning summary.

## Pending for the author

- Results headline in the README (after reviewing `docs/results/`).
- Publishing the dated 2026/27 forecast.

## Log
