---
name: OlivEye
description: Olive groves of Jaén and Granada seen from Sentinel-2, with an honestly validated production estimate set against the official aforo.
colors:
  ink: "#163300"
  ink-strong: "#0e0f0c"
  spruce: "#054d28"
  lime: "#9fe870"
  mist: "#e2f6d5"
  fog: "#e8ebe6"
  paper: "#ffffff"
  body: "#454745"
  muted: "#6a6c6a"
  hairline: "#868685"
  rule: "#d6dad3"
  signal: "#0b4c72"
  alarm: "#cb272f"
  on-ink: "#e2f6d5"
  on-ink-muted: "#b8d3a6"
  map-ground: "#f2f3ef"
  ndvi-1: "#f4fbef"
  ndvi-2: "#e2f6d5"
  ndvi-3: "#9fe870"
  ndvi-4: "#4f9a2f"
  ndvi-5: "#054d28"
  ndvi-6: "#163300"
  ndmi-1: "#eef5f9"
  ndmi-2: "#c6dceb"
  ndmi-3: "#9cc3da"
  ndmi-4: "#6aa2c6"
  ndmi-5: "#3d82ad"
  ndmi-6: "#0b4c72"
typography:
  headline:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "clamp(22px, 2vw, 28px)"
    fontWeight: 800
    lineHeight: 1.12
    letterSpacing: "-0.03em"
  section-title:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "clamp(24px, 2.4vw, 32px)"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.03em"
  wordmark:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 800
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    letterSpacing: "-0.01em"
  kpi-value:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
    fontFeature: "\"tnum\""
  body:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "\"cv11\", \"ss01\""
  label:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
  caption:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.45
  axis:
    fontFamily: "Inter Variable, Inter, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 400
rounded:
  swatch: "3px"
  row: "8px"
  card: "10px"
  panel: "28px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  section: "64px"
  gutter: "clamp(16px, 4vw, 40px)"
  bar-height: "56px"
  content: "1200px"
components:
  top-bar:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.on-ink}"
    height: "{spacing.bar-height}"
  campaign-select:
    backgroundColor: "{colors.lime}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "6px 36px 6px 16px"
  segmented-ink-checked:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "4px 14px"
  segmented-paper-checked:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "4px 14px"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "7px 18px"
  button-secondary-hover:
    backgroundColor: "{colors.fog}"
  input-search:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.body}"
    rounded: "{rounded.card}"
    padding: "9px 12px 9px 36px"
  kpi-tile:
    backgroundColor: "{colors.fog}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "12px 16px 10px"
  floating-panel:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.panel}"
    padding: "16px 18px"
  list-panel:
    backgroundColor: "{colors.fog}"
    width: "320px"
  method-callout:
    backgroundColor: "{colors.mist}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "24px 28px"
---

# Design System: OlivEye

AI-readable design system for the OlivEye web app (Phase 5: Next.js + MapLibre). Tools such as
the `impeccable` skill read this file before any UI work. This version describes the **built**
single page (`web/`); tokens live in `web/app/globals.css` and the data ramps in `web/lib/scale.ts`.

**Reference:** inspired by the *Wise* style on [styles.refero.design](https://styles.refero.design/style/367c0c6e-73a7-441c-a8ff-91d139ac60dc)
(deep moss greens, lime accent, flat surfaces, pill controls). Chosen because moss/olive greens are
the subject's own colours and lime reads as "fresh vegetation", which is literally what NDVI
measures. Adapted for a data product: calmer display type, data palettes added, no brand assets.

## Overview

**Creative North Star: "The Moss Workbench"**

A forest-ink bar, a white canvas and fog work panels: the page answers first, then hands the
visitor a working map and charts to check the answer. The product mode is **Operate / Read**, not
Persuade: a map, time series and a prediction-vs-aforo comparison that people read carefully.
Precision and restraint over spectacle. One honest sentence leads the page; everything else is data.

The world is the moss palette of the reference, made quieter. Surfaces are flat and separated by
hairlines; the only lift belongs to panels that float over the map. Lime is scarce on purpose: it
marks the one active choice (the campaign) and the campaign's place in every chart. Inter carries
everything, with tabular numbers wherever a value can be compared.

**Key Characteristics:**
- Verdict band first (question, answer, forecast vs aforo, error vs baseline), workbench second.
- Forest-ink top bar; lime only for the active campaign and its highlight.
- Flat white and fog surfaces, 1px hairline rules, one floating shadow.
- Single-hue sequential ramps (moss for NDVI, water blue for NDMI), never a rainbow.
- Colour never carries meaning alone: line style, marker, hatch or label always backs it up.
- Light theme only for now.

## Colors

Deep moss and forest ink on white, one lime accent, and a single official blue.

### Primary
- **Forest Ink** (`ink`): top bar, footer, secondary-button borders and text, checked state of
  segmented controls on paper, method-callout text, map outlines (35 % opacity).
- **Fresh Lime** (`lime`): the campaign selector pill, the selected campaign's highlight in
  charts, text selection, the skip link and the eye in the wordmark. Never text on white.

### Secondary
- **Spruce** (`spruce`): OlivEye's own numbers and lines (prediction, KPI values, forecast
  diamond), focus rings, the selected list row's inset outline, the verdict's "Todavía no".
- **Signal Blue** (`signal`): everything official (aforo values, aforo lines and bars) and links.

### Neutral
- **Ink Black** (`ink-strong`): headings, real production dots, selected-municipality outline on
  the map, tooltip background.
- **Fog** (`fog`): KPI tiles, the municipality list panel, chart gridlines, hover on paper
  controls, and the **no-data** colour on the map and legend.
- **Mist** (`mist`): method callout, zebra rows in data tables, the underline wash on the verdict
  answer. Also used as `on-ink` text on the forest-ink bar.
- **Paper** (`paper`): page canvas, floating panels, search input, track of the error bars.
- **Body Grey** (`body`), **Muted Grey** (`muted`), **Hairline** (`hairline`): body text; helper
  text and axis ticks; input borders and the province-mean baseline bar.
- **Rule** (`rule`): 1px dividers between bands, panels, table headers and chart axes.
- **Lichen** (`on-ink-muted`): secondary text on the forest-ink bar and footer.
- **Map Ground** (`map-ground`): plain ground the map falls back to when the basemap cannot load,
  so the measured olive area still draws.
- **Alarm** (`alarm`): reserved for errors and the over-estimation side of the diverging error
  scale. Defined but not used on the shipped page.

### Data colours (charts and map)
- **Series:** OlivEye prediction = spruce solid line (2.5px) with dots; official aforo = signal
  dashed (6 4) with dots; real production = ink-black dots (4.5px, white ring) on a 1px line;
  2026/27 forecast = spruce diamond with a ×/÷2 error bar.
- **NDVI (sequential, single hue, 6 classes):** `ndvi-1` → `ndvi-6`, pale wash → moss → forest ink.
- **NDMI (sequential, water, 6 classes):** `ndmi-1` → `ndmi-6`, pale water → deep signal blue.
  Expanded from the 4 steps planned before the build so it has the same six classes as NDVI.
- **Error vs actual (diverging, planned):** under `signal` ← neutral `fog` → over `alarm`.
- Validate every palette for colour-blind safety (deuteranopia) before shipping.

### Named Rules
**The One Lime Rule.** Lime marks one thing per view: the active campaign. The selector is lime,
and the same campaign is highlighted in lime (30 % opacity) in the province chart, with its own
legend entry. No other control or text is lime.

**The Official Blue Rule.** Signal blue belongs to the Junta's aforo and to links. OlivEye's own
numbers are spruce; nothing of ours is ever blue.

**The Same Colour, Same Value Rule.** Map classes are quantile breaks computed once over **all
campaigns**, so a colour means the same index value in every year. Missing data is always fog.

## Typography

**Display Font:** Inter Variable (with Inter, system-ui)
**Body Font:** Inter Variable
**Label/Mono Font:** Inter with `font-variant-numeric: tabular-nums` for every comparable number

**Character:** One family, weight does the hierarchy: 800 with tight tracking for headings, 700
for numbers and titles, 600 for labels, 400 for reading. Character variants `cv11` and `ss01` on.

### Hierarchy
- **Headline** (800, clamp 22–28px, 1.12, −0.03em): the verdict question; max 22ch.
- **Section title** (800, clamp 24–32px, 1.15, −0.03em): page sections (province production).
- **Wordmark** (800, 20px, −0.03em): "OlivEye" in the top bar.
- **Title** (700, 15–20px): panel, legend, chart and callout titles; series drawer 18px.
- **KPI value** (700, 22px, −0.02em, tabular): forecast and aforo tonnes; error % at 18px.
- **Body** (400, 16px, 1.6): reading text; verdict detail 15px max 58ch; leads 17px max 68ch.
- **Label** (600, 14px): control faces, list meta, tile titles, table row heads.
- **Caption** (400, 12–13px, 1.45, muted): sources, notes, ranges, legend help.
- **Axis** (400, 11px, muted): chart ticks and legend scale ticks.

The 56px display size planned before the build is not used: the largest shipped size is 32px.

### Named Rules
**The Tabular Rule.** Any number that sits next to another number uses tabular figures and
carries its unit ("392 kt", "44 %").

## Layout

- **Model:** a 56px forest-ink top bar; a verdict band (max 1440px, answer column + two
  comparison tiles); a full-height **workbench** (320px fog list panel + map, height
  `max(560px, 100vh − 56px)`); then content sections at max 1200px (province charts, method,
  footer).
- **Rhythm:** 4px base. Element gaps 8–12px, panel padding 16–24px, section padding 64px.
  Side gutter `clamp(16px, 4vw, 40px)`.
- **Breakpoints:** ≤1080px the verdict stacks; ≤860px the workbench stacks (list capped at 220px
  above a 78vh map, min 480px) and province charts go to one column; ≤640px tiles stack, floating
  panels tighten and the top bar becomes **static** (not sticky) so it never covers the map.
- **Map:** the map area may go full-bleed inside the workbench; legend floats top-left, the series
  drawer floats along the bottom.

## Elevation & Depth

Flat by default. Depth comes from tonal layering (paper over fog) and 1px rules. A single soft
shadow lifts only what floats over the map.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 8px 24px rgba(14,15,12,0.14), 0 1px 3px rgba(14,15,12,0.08)`):
  map legend, series drawer and hint, map tooltip, MapLibre control group.
- **Swatch edge** (`box-shadow: inset 0 0 0 1px rgba(14,15,12,0.12–0.18)`): keeps pale ramp
  swatches visible on white.

### Named Rules
**The Only Floaters Rule.** Shadows belong to panels that sit over the map. Everything in the page
flow is flat. No gradients, no glassmorphism, no glows.

## Shapes

- **Pills** (9999px): campaign selector, segmented controls, secondary buttons, error-bar tracks,
  the drawer's close button, the map hint.
- **Cards** (10px): KPI tiles, chart panels, search input, method callout, tooltips. List rows 8px.
- **Floating panels** (28px): map legend and series drawer.
- **Swatches** (3–4px): legend and list swatches.
- Hairline borders (1px `rule`, or `hairline` on inputs).

## Components

### Navigation (top bar)
- Forest-ink bar, sticky at 56px on desktop, static at ≤640px. Wordmark left (eye mark with a
  lime iris). Right: campaign selector, NDVI|NDMI and ES|EN segmented controls, labels in lichen.

### Campaign selector
- A **lime pill dropdown** (native `<select>`, ink text 700, tabular, ink chevron), not a
  segmented control: ten campaigns (2017/18–2026/27) do not fit a pill row on a phone. Defaults
  to 2026/27. Focus: 2px white outline.

### Segmented controls
- Pill group of native radios (keyboard-accessible), faces 14px/600, padding 4px 14px,
  transitions 0.2s. Used for **NDVI|NDMI**, **ES|EN** and the **list sort** (index | A–Z).
- **On ink:** translucent mist border, mist text, hover wash 12 %, checked = paper face, ink text.
- **On paper:** rule border, body text, hover fog, checked = ink face, paper text.

### Buttons
- **Secondary:** outlined pill (1px ink border, ink text 600, paper fill, hover fog), e.g. "show
  table". **Icon:** 32px round close button with a rule border.
- There is no filled primary button on the page; lime fill is spent on the campaign selector.

### KPI tiles (verdict)
- Fog cards (10px). Forecast tile: a small table of OlivEye (spruce) vs aforo (signal) per
  province, range under the OlivEye value. Error tile: horizontal bars on paper pill tracks:
  **OlivEye** spruce solid, **province-mean baseline** hairline grey, **aforo** signal with a
  diagonal **hatch** (secondary, non-colour encoding). Caption states the validation scheme.

### Inputs / Fields
- Search: paper fill, 1px hairline border, 10px radius, muted search icon. Focus: 2px spruce
  outline, spruce border.

### Municipality list
- Fog panel, 320px. Rows: swatch · name (+ muted province) · tabular value. Hover: paper at 70 %.
  Selected: paper fill with a 1.5px spruce inset outline.

### Map
- Measured olive area (not municipal boundaries) filled by class at 0.88 opacity (1 on hover),
  ink outlines at 35 %, selected municipality outlined 2.2px ink black. Positron basemap; if it
  cannot load, a plain map-ground background. Tooltip: ink-black card, paper text.
- **Legend:** floating panel (28px; 18px at ≤640px): title, help, six swatches with ticks, end
  labels, no-data swatch, note. Help and note hide on phones.

### Series drawer
- Floating panel along the map bottom, rises in (0.35s); monthly NDVI (spruce) or NDMI (signal)
  line with the campaign's image window shaded lime. Before selection, a pill hint.

### Charts
- Recharts, fog gridlines, rule axis lines, 11px muted ticks, 10px tooltip. The selected
  campaign is a lime band at 30 %. A key above the charts names every series by mark.
- **Data table:** zebra with mist, right-aligned tabular numbers, 12px muted headers.

### Method callout
- Mist card (10px, 24×28px padding, max 76ch), ink text, explains leave-one-campaign-out.

## Do's and Don'ts

### Do:
- **Do** keep lime to the active campaign and its highlight (One Lime Rule).
- **Do** pair every colour encoding with a line style, marker, hatch or label.
- **Do** compute map breaks over all campaigns and paint missing data fog.
- **Do** show every metric with its baseline and validation scheme.
- **Do** use tabular numbers with units for anything comparable.
- **Do** state source and date under every chart.

### Don't:
- **Don't** use lime for body text or for more than one thing per view.
- **Don't** colour OlivEye's own numbers signal blue.
- **Don't** use rainbow/jet colour maps for NDVI or NDMI.
- **Don't** add shadows to in-flow surfaces, or gradients, glassmorphism or glows.
- **Don't** make the top bar sticky on phones.

## Copy

- Spanish first, English toggle. Plain words: "producción estimada", "aforo oficial".
- Always state the source and date under charts ("Fuente: Junta de Andalucía, aforo 2026/27").

## Themes

- **Light:** default when the system asks for it (`color-scheme: light`).
- **Dark:** shipped 2026-10-25. Follows the system until the visitor uses the toggle in the top
  bar (remembered in `localStorage`). Canvas `#0e0f0c`, surfaces `#1c2318` / `#16240f`, text
  `#c9d2c4`, headings `#f1f8ec`, lime unchanged; the top bar and footer keep the forest ink
  (`--brand`). Spruce (OlivEye) becomes `#7ccf8a` and signal (aforo) `#6cb2dd` to keep 4.5:1.
- Components use tokens only. Charts and the map cannot read CSS variables, so they take the same
  values from `web/lib/theme.ts`; a test keeps both in sync.
- Map ramps: on the dark basemap brighter means more (`RAMPS_DARK` in `web/lib/scale.ts`), because
  the light ramps' darkest classes vanish into a near-black ground. The legend shows the active ramp.
