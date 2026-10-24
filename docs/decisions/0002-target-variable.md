# ADR 0002 — Target variable: final olive oil production per province

- **Status:** accepted (confirmed by the author on 2026-10-24; see "Open")
- **Date:** 2026-10-24

## Context

The model predicts olive oil production (tonnes) per province and campaign, and is compared with
the Junta's *aforo*. The natural source for actual production is AICA (Agencia de Información y
Control Alimentarios), but AICA does not publish a machine-readable provincial series: provincial
figures only appear in press releases and in sector reports that quote it.

Each Junta aforo PDF publishes, per province, the forecast **and its % variation versus the
previous campaign's final production**. Back-solving gives the final production the Junta itself
uses as reference: `final(t-1) = aforo(t) / (1 + variation)`.

Check against AICA (Andalucía totals): 2023/24 derived 578,100 t vs AICA 580,464 t (−0.4 %);
2018/19 derived 1,461,500 t vs AICA 1,464,286 t (−0.2 %).

## Decision

- **Target:** `oil_prev_final_t_derived` from the aforo tables (`oliveye.pipeline.production`),
  re-indexed to the campaign it describes, plus the same derivation from official press releases
  for campaigns without PDF (`docs/sources/aforo_press_releases.csv`).
- Values are flagged as **derived** everywhere (column name, docs, web). Rounding of the inputs
  gives about ±0.5 % uncertainty, far below the year-to-year variation (±50 %).
- **Baseline to beat:** the aforo itself, plus "same as last campaign" and "5-campaign mean".

## Consequences

- Available today for Jaén: 2015/16, 2018/19 and 2020/21–2025/26 (8 campaigns). Missing:
  2016/17, 2017/18, 2019/20 — to be filled from the Junta's *Anuario de Estadísticas Agrarias*
  or AICA press releases, each value with its source.
- Interview line: "AICA has no open provincial series, so I recover the Junta's own final
  figures from the variation it publishes, and validate them against AICA's regional totals."

## Open

- Replace with a primary AICA or yearbook series if one becomes available; keep the derived one
  as a cross-check.
