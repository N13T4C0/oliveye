# ADR 0004 — XGBoost is not used for the main model

- **Status:** accepted
- **Date:** 2026-10-25

## Context

The project stack lists XGBoost, and boosted trees are the default choice for tabular data.
OlivEye's modelling table, however, has ~16 rows (province × campaign, ADR 0003).

## Decision

Ridge regression on four a-priori features is the main model. XGBoost is kept only as a
documented experiment (`scripts/experiment_xgboost.py`, optional extra `experiments`), run with
the same leave-one-campaign-out as everything else.

## Evidence

| Run | Rows | XGBoost MAPE | "Repeat last campaign" MAPE |
|---|---|---|---|
| 2026-10-25, provisional (Jaén features from 1 municipality) | 16 | 84.1 % | 43.3 % |

To be refreshed with the full 85-municipality data; the conclusion is not expected to change.

## Why

- A tree ensemble learns splits from data; with ~14 training rows per fold each split is
  decided by a handful of campaigns, and its predictions cannot extrapolate beyond the range seen.
- Ridge is linear, shrinks coefficients and its behaviour with few rows is well understood.
- Interview line: "I tried XGBoost under the same validation; with 16 rows it was worse than
  repeating last year's harvest, so I chose the model the data could support."
