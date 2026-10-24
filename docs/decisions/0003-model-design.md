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
| 2 | Data cut at the end of August of the campaign's first year | Same information as the aforo (published late September) |
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
