# Dated forecast — campaign 2026/27

**Published 2026-10-25**, before the Junta's final production for 2026/27 is known. It will be
scored against that figure when it is published (expected autumn 2027). Reviewed by
`oliveye-auditor` (PASS with the caveats below). Produced by `scripts/forecast.py`.

| Province | OlivEye forecast | 80 % interval | Official aforo (Junta, Oct 2026) |
|---|---|---|---|
| Jaén | **392,000 t** | 196,000 – 785,000 t | 575,000 t |
| Granada | **96,000 t** | 48,000 – 193,000 t | 106,700 t |

How it was made: the main model (ADR 0003) fitted on all 16 known province-campaigns, with
satellite and climate data up to **August 2026** (spring NDVI, summer NDMI, May heat days) and
last campaign's production. The interval is the conformal-style ×/÷ 2.0 from the
leave-one-campaign-out residuals.

## Caveats

1. **It is essentially the province mean.** The final model chose the strongest shrinkage
   (alpha = 1000), as in 8 of 9 validation folds: the satellite and climate features barely move
   the forecast. Read it as "a typical year for this province", not as a satellite reading of
   this year's crop.
2. **Dated with the aforo, not before it.** The lag feature (2025/26 production: Jaén 389,000 t,
   Granada 107,300 t) is derived from the 2026/27 aforo's % variation (ADR 0002), which was
   published in mid-October 2026. In practice that production is almost fully known by August
   from AICA's monthly declarations, but the exact number came out with the aforo.
3. **The aforo is not an input.** It is shown only for comparison.
4. **The interval is approximate:** 16 residuals from 9 campaigns, with the two provinces of a
   campaign correlated.
5. Validation of the method so far (leave-one-campaign-out): model MAPE 44 % vs aforo 12 %
   ([results](README.md)). The aforo is the better forecast; this one exists to be scored
   honestly, out of sample.
