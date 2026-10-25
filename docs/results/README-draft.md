# DRAFT — Results section for the README (for the author to review)

> Status: **filled from the reviewed 2026-10-25 run** ([`README.md`](README.md) in this folder).
> The author decides the headline and whether it goes into the README.

## Results

**Question:** with satellite (Sentinel-2) and climate data up to August, can a simple model
forecast a province's olive oil harvest as well as the official forecast (*aforo*) published by
the Junta de Andalucía in October (which also uses field fruit counts)?

**Short answer:** not yet. With 9 campaigns the model reduces to the province average (44 %
MAPE, the same as repeating last year's harvest), while the aforo, which also counts fruit in the
field in October, has 12 %: about 3–4× lower and closer in 6 of 9 campaigns (suggestive, not
conclusive: p = 0.055).

| Model (same 15 rows, 9 campaigns) | MAPE | Median APE | Campaigns closer than the aforo |
|---|---|---|---|
| Aforo (Junta, October, field counts) | 11.9 % | 11.2 % | – |
| **OlivEye — Ridge, data to August** | 44.1 % | 30.7 % | 3 / 9 (p = 0.055) |
| Repeat last campaign | 44.0 % | 28.6 % | 1 / 9 |
| Province mean | 45.4 % | 30.6 % | 3 / 9 |

![Real production, aforo and OlivEye per campaign](docs/results/figures/production_vs_aforo.png)

### How it was validated

- **Leave-one-campaign-out:** each campaign (both provinces) is predicted by a model that never
  saw it, nor the following campaign, whose "last year's production" feature would reveal it.
- **Forward check:** training only on earlier campaigns gives 53.9 % MAPE vs 12.4 % for the
  aforo (5 campaigns, too few for inference).
- Ridge regression on 4 features fixed in advance (last year's production, May heat days,
  summer NDMI, spring NDVI), with the province level unpenalised (ADR 0003). The selected
  shrinkage removes the features: the model is, in practice, the province mean.
- 80 % interval: forecast ÷/× 2.0, from the 16 out-of-sample errors (coverage not validated).

### Limitations (read before quoting a number)

- Only 9 campaigns since Sentinel-2 (2015): every metric is noisy.
- 15 of 16 "real" production values are derived from the Junta's aforo variations (ADR 0002).
- Olive trees alternate heavy and light years; the aforo uses field fruit counts in October that
  a satellite cannot see in August.
- Granada lacks reliable figures for 2016/17 and 2017/18 (rows dropped, not imputed).
- Features cover 80.1 % of Jaén's and 80.6 % of Granada's SIGPAC olive area.

### Next test

A dated 2026/27 forecast was published on 2026-10-25 (Jaén 392 kt, Granada 96 kt, vs aforo
575 / 106.7 kt; [details](forecast-2026-27.md)) and will be scored when the Junta's final figure
is known.
