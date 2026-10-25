# ADR 0007: More campaigns from Sentinel-2 back to 2015, not Landsat

- **Status:** accepted (code and dry runs). The real extraction waits for the author's approval.
- **Date:** 2026-10-25

## Context

The model has 9 campaigns (15 like-for-like province-campaigns), and that sample size is what
limits it (ADR 0003). The TODO suggested Landsat to reach back before 2015.

What the Copernicus Data Space Ecosystem (CDSE) actually offers, checked on 2026-10-25:

| Source on CDSE | Level | From | Problem |
|---|---|---|---|
| Landsat-8 | **Level-1 only** (top-of-atmosphere) | January 2015 | No surface reflectance, a different sensor, and nothing before 2015 |
| Sentinel-2 L2A | Level-2A (surface reflectance) | **4 July 2015** (S2A; S2B from March 2017) | None: same product as the current series |

Our series starts in October 2016 only because one job is capped at 120 months, not because of
the archive.

## Decision

1. Extend **Sentinel-2 L2A** for the same 86 municipalities to **October 2015 – September 2016**
   (one 12-month job per municipality, tag `2015-2016`). This covers the feature window of
   campaign 2016/17 (spring NDVI March–May 2016, summer NDMI June–August 2016).
2. Do not use Landsat: Level-1 top-of-atmosphere indices would need a cross-calibration against
   Sentinel-2, and they would add at most campaign 2015/16. That campaign also lacks the previous
   year's production (2014/15), which the model needs as a feature.
3. `oliveye.models.sources.INDEX_PERIODS` lists the extraction periods. `load_monthly` joins them
   into one series per municipality **before** the causal outlier filter. On a month that appears
   in two periods, the main run wins. One-off test extractions are never read.

## Expected gain (honest)

- **+1 campaign, +1 row:** Jaén 2016/17. It has a final figure (503,500 t, derived from the
  2017/18 aforo), an aforo (542,000 t) and the lag (2015/16, 528,800 t). That takes us from
  15 to 16 like-for-like rows and from 9 to 10 campaigns.
- Granada 2016/17 has no final figure in our sources, so it adds nothing until one is found.
- With S2A alone the 2015/16 composites have about half the images of later years, so a monthly
  median has fewer clear observations. `valid_cells` makes the thin months visible.
- Cells use today's SIGPAC olive parcels, the same assumption as the main run. A few
  superintensive groves planted after 2015 may be included before they existed.

## Cost

Martos cost 6 credits for 12 months (2026-10-24), and the 86 municipalities cost 1,459 credits in
total for 120 months. An estimate for 86 × 12 months is 350–550 credits, within the monthly
allowance and the workflow budget (`OPENEO_CREDIT_BUDGET` 3,100; 1,459 spent so far). The 86
dry runs cost 0 credits.

## Interview line

"Before reaching for another satellite, I checked what the archive really had. Landsat on CDSE
was Level-1 and only from 2015, while Sentinel-2 L2A started in July 2015. So the cheapest honest
gain was one more campaign with the same sensor and no cross-calibration."
