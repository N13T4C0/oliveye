# ADR 0003 — Model design for province × campaign production

- **Status:** accepted (agreed with the author in a `/grill-me` session, 2026-10-24)
- **Date:** 2026-10-24

## Context

The target is the final olive oil production per province and campaign (ADR 0002). Only ~13
province-campaign rows exist (Jaén and Granada, Sentinel-2 era). With so little data the main
risk is not under-fitting but **fooling ourselves**: over-fitting, leakage and metrics chosen
after looking at the results.

## Decisions

| # | Decision | Why (one line) |
|---|---|---|
| 1 | One model for both provinces, with a province indicator | 7 rows per province are not enough for separate models |
| 2 | Data cut at the end of August of the campaign's first year | Before the aforo, which is published in mid/late October with field fruit counts (see amendment 2a) |
| 3 | Predict `log(production)`, report tonnes | Effects are multiplicative; big years must not dominate |
| 4 | Main model is independent of the aforo; an *aforo corrector* is a secondary experiment | "My model vs the official one" is the honest portfolio story |
| 5 | Leave-one-campaign-out, both provinces of a campaign held out together | Holding out one province leaks that year's weather |
| 6 | Metrics: MAPE and number of campaigns closer than the aforo; baselines: last campaign, 5-campaign mean, aforo | Simple, interpretable, comparable on the same campaigns |
| 7 | Four features fixed a priori: lagged log production (alternate bearing), May days > 32 °C (heat at flowering), summer NDMI (Jun–Aug), spring NDVI (Mar–May) | No feature search: with 13 rows any search inflates metrics |
| 8 | Fill production gaps (2016/17, 2017/18, 2019/20; Granada also 2018/19) from cited sources before modelling | The lag feature would otherwise drop rows |
| 9 | Ridge as the main model; XGBoost only as a documented negative test | Tree ensembles need hundreds of rows |
| 10 | Prediction intervals from leave-one-campaign-out relative errors | A point forecast without a range misleads |
| 11 | MLflow local (git-ignored) + results table in `docs/results/` | Traceable runs; a readable summary for reviewers |
| 12 | Ridge alpha chosen by nested leave-one-campaign-out in each fold, grid {0.1, 1, 10} | Choosing alpha on the outer folds would leak |
| 13 | Standardisation fitted inside each fold (`sklearn.pipeline.Pipeline`) | Scaling with held-out data leaks |
| 14 | Municipality → province: weighted by SIGPAC olive hectares; climate from each municipality's ERA5 cell | Large olive municipalities must count more |
| 15 | Publish a dated 2026/27 forecast next to the aforo (575 kt Jaén, 106.7 kt Granada) | A genuine out-of-sample test when the real figure arrives |
| 16 | Rows whose gaps cannot be filled from a reliable source are dropped, never imputed | Imputing would contaminate the alternate-bearing feature |
| 17 | Code: `models/dataset.py`, `train.py`, `evaluate.py`, `scripts/train_models.py`, notebook 04 | Notebooks only plot; logic is tested in the package |

## Consequences

- Results will be modest and noisy; the README reports them with intervals and the number of
  campaigns used, never a single headline number.
- `oliveye-auditor` (leakage checks) and `model-qa` review the metrics before they are published.

## Amendment — 2026-10-25 (statistician review, before results on the full data)

Method corrections decided before seeing results on the 85-municipality data. None of them adds
or searches features. All except 13a came from the statistician's review of the design; 13a came
from a defect visible in the provisional results and is labelled as such.

| # | Change | Why (one line) |
|---|---|---|
| 5a | When campaign t is held out, campaign t+1 is also removed from training (outer and inner folds) | t+1's lag feature *is* t's real production: a leak the first test did not catch (now tested end to end) |
| 6a | Every model scored on the same rows; also median APE, mean \|log error\|, per-campaign errors and an exact sign-flip test vs the aforo (p-values descriptive, no multiplicity correction) | Like-for-like comparison; the two provinces of a campaign are not independent evidence |
| 6b | Extra references: province mean, and a lag + province model | Shows whether satellite and climate add anything over the simplest models |
| 10a | Interval: conformal-style symmetric half-width on log residuals (rank ⌈(n+1)·0.8⌉, capped at n) next to the empirical quantiles | Distribution-free and simple; coverage is approximate because LOCO residuals are not strictly exchangeable |
| 12a | Alpha grid `logspace(-1, 3, 9)`, one-standard-error rule (largest alpha within 1 SE of the best) | Prefer more shrinkage when the data cannot tell alphas apart |
| 13a | `ProvinceAnomalyRidge`: province level unpenalised; features centred on their province mean, clipped to the training range, standardised; Ridge fits within-province anomalies | NDMI/NDVI levels are confounded with province, and shrinking the province indicator pulled both provinces towards a pooled mean. **Driven by results:** found on the provisional run (leave-one-campaign-out, 15 like-for-like rows, Jaén features from 3.7 % of its olive area): Ridge MAPE 80.8 % → 44.9 %, vs province mean 45.4 %, last campaign 44.0 %, aforo 11.9 %. It removes a defect (infinite shrinkage now gives the province mean) and adds no feature |
| 13b | Forward-chaining check (train only on earlier campaigns) reported next to leave-one-campaign-out; inside it, alpha is chosen by leave-one-campaign-out among those earlier campaigns only | Leave-one-campaign-out also trains on future years; an inner forward split would leave too few folds to pick alpha |
| 2a | Correction (model-qa, 2026-10-25): the aforo is published 16–28 October and uses field fruit counts, not late September | The comparison is *not* like-for-like in information: the August cut handicaps the model; results must say so |
| 15a | The 575 kt (Jaén) and 106.7 kt (Granada) of decision 15 are the **aforo's** 2026/27 figures; the model's own dated forecast is not computed yet | Never present the aforo's numbers as the model's forecast |
