---
version: 1
slug: "web-app-page-tsx"
primary_target: "web/app/page.tsx"
related_targets: []
---

# Surface brief — OlivEye web (single page)

Scope: `web/` single page (Spanish default, English toggle). Mode: **Operate** (with a Read
section for method). Audiences: evaluators (recruiters, data engineers) and the olive sector
(PRODUCT.md). Data from the OlivEye API (`/municipalities`, `/municipalities/{p}/{m}/indices`,
`/provinces/{p}/production`, `/models/summary`, `/forecast`, `/map/municipalities`).
Structure chosen by the assistant at the author's request ("lo que tú recomiendes"): verdict
band + workbench (hybrid of the dealt lead and dealt #1). Roll ran degraded (no challengers).

## Direction contract

THESIS: The page answers first and lets you check it: one honest sentence and four numbers,
then a working map where every colour is the olive area the satellite actually measured. It
refuses the category default of a full-bleed decorative map with a marketing hero.

OWN-WORLD: DESIGN.md's moss world. Forest-ink top bar (#163300) with lime only for the active
campaign; white canvas, fog (#e8ebe6) work panels with hairlines, Inter with tabular numbers,
pills for segmented controls, NDVI single-hue moss ramp, NDMI water ramp, aforo always signal
blue dashed, OlivEye spruce solid, real production ink dots.

STORY: Visitor reads "¿Puede el satélite anticipar la cosecha de aceite? Todavía no" with the
2026/27 forecast vs aforo and model vs aforo error, understands why (method), then finds their
municipality, sees ten years of NDVI/NDMI, and compares provinces campaign by campaign.

FIRST VIEWPORT: (1440×900) 56px ink top bar: OlivEye wordmark left; campaign segmented select
(2017/18…2025/26), NDVI|NDMI toggle and ES|EN right. Verdict band (~190px): question + answer
left (32px), four KPI tiles right (forecast Jaén, aforo Jaén, OlivEye error 44 %, aforo error
12 %, each with its baseline line). Workbench fills the rest: 320px fog list panel (search,
sortable municipality list with index value and swatch) left; map right with floating legend
card (radius 28) and selected-municipality series drawer along the map's bottom.

FORM: verdict-first + workbench, positions 1 and 7 of the ordered list; seed: bd23bf9d75cc5187.
Signature move: campaign selection recolours the measured-olive map and highlights that
campaign in the province production chart (linked state).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
