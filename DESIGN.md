# DESIGN.md — OlivEye

AI-readable design system for the OlivEye web app (Phase 5: Next.js + MapLibre). Tools such as
the `impeccable` skill read this file before any UI work.

**Reference:** inspired by the *Wise* style on [styles.refero.design](https://styles.refero.design/style/367c0c6e-73a7-441c-a8ff-91d139ac60dc)
(deep moss greens, lime accent, flat surfaces, pill controls). Chosen because moss/olive greens are
the subject's own colours and lime reads as "fresh vegetation", which is literally what NDVI
measures. Adapted for a data product: calmer display type, data palettes added, no brand assets.

## Product mode

- **Operate / Read**, not Persuade: a map, time series and a prediction-vs-aforo comparison that
  people read carefully. Precision and restraint over spectacle.
- One hero sentence on the landing view; everything else is data.

## Colour tokens

| Token | Hex | Use |
|---|---|---|
| `--ink` | `#163300` | Primary text on light, nav, dark sections ("forest ink") |
| `--ink-strong` | `#0e0f0c` | Display headings |
| `--spruce` | `#054d28` | Secondary dark green, selected states on light |
| `--lime` | `#9fe870` | **One** primary action or active state per view; never for text on white |
| `--mist` | `#e2f6d5` | Pale green wash: highlighted rows, info callouts |
| `--fog` | `#e8ebe6` | Cards, dividers, map control backgrounds |
| `--paper` | `#ffffff` | Page canvas |
| `--body` | `#454745` | Body text |
| `--muted` | `#6a6c6a` | Helper text, axis labels |
| `--hairline` | `#868685` | Input borders, 1px rules |
| `--signal` | `#0b4c72` | Official data (aforo), links |
| `--alarm` | `#cb272f` | Errors, over-estimation in diverging scales |

Dark theme: canvas `#0e0f0c`, surfaces `#163300`, text `#e2f6d5`, lime unchanged.

## Data colours (charts and map)

Colour never carries meaning alone: every series also has a label, a line style or a marker.

- **Series:** OlivEye prediction = `--spruce` solid line; official aforo = `--signal` dashed;
  actual production (AICA) = `--ink-strong` dots. Uncertainty band = `--spruce` at 15 % opacity.
- **NDVI (sequential, single hue):** `#f4fbef → #e2f6d5 → #9fe870 → #4f9a2f → #054d28 → #163300`.
- **NDMI (sequential, water):** `#eef5f9 → #9cc3da → #3d82ad → #0b4c72`.
- **Error vs actual (diverging):** under `#0b4c72` ← neutral `#e8ebe6` → over `#cb272f`.
- Validate every palette for colour-blind safety (deuteranopia) before shipping.

## Typography

- **Inter** for everything (UI, body, numbers with `font-variant-numeric: tabular-nums`).
- Display: Inter 800, tracking −0.03em, line-height 1.0. Max 56px (not the 100px+ of the reference).
- Scale (px): 12 · 14 · 16 · 18 · 24 · 32 · 44 · 56. Body 16/1.6.
- Numbers in KPI tiles: Inter 700, tabular, with unit in `--muted` at 60 % size ("445.000 t").

## Space, shape, elevation

- 4px base unit. Element gap 8–12, card padding 24, section gap 64. Max content width 1200px; the
  map may go full-bleed.
- Radii: pills (buttons, tags, segmented controls) 9999px; cards and inputs 10px; large panels 28px.
- Flat. 1px hairline borders; one soft shadow only for floating map panels.
- No gradients, no glassmorphism, no glows.

## Components

- **Primary button:** lime fill, ink text, pill. **Secondary:** outlined pill, ink border.
  Pair a filled button with a text link, never two filled buttons.
- **Segmented control:** campaign selector (2015/16 … 2026/27) and index toggle (NDVI / NDMI).
- **KPI tile:** label (14, muted) · value (32, tabular) · delta vs aforo (14, signal/alarm).
- **Map panel:** floating card (radius 28, shadow), legend with the exact palette above.
- **Data table:** zebra with `--mist`, right-aligned numbers, units in the header.
- **Callout "Method":** mist background, explains leave-one-campaign-out in two sentences.

## Copy

- Spanish first, English toggle. Plain words: "producción estimada", "aforo oficial".
- Always state the source and date under charts ("Fuente: Junta de Andalucía, aforo 2026/27").

## Do not

- Use lime for body text or for more than one action per view.
- Show a metric without its baseline and validation scheme.
- Use rainbow/jet colour maps for NDVI.
