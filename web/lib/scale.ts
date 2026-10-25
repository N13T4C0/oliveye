/**
 * Colour scales and number formatting for the map, legend and charts.
 * Palettes come from DESIGN.md: single-hue sequential ramps, never a rainbow.
 */

import type { IndexKey } from "./types";

export const RAMPS: Record<IndexKey, readonly string[]> = {
  // NDVI: pale wash → moss → forest ink (more vigour = darker green).
  ndvi_spring: ["#f4fbef", "#e2f6d5", "#9fe870", "#4f9a2f", "#054d28", "#163300"],
  // NDMI: pale water → deep signal blue (more leaf water = darker blue).
  ndmi_summer: ["#eef5f9", "#c6dceb", "#9cc3da", "#6aa2c6", "#3d82ad", "#0b4c72"],
};

/**
 * Dark-theme ramps: on a near-black map the light ramps' darkest classes vanish into the ground,
 * so here more vigour (or more water) is brighter. The legend always shows the active ramp.
 */
export const RAMPS_DARK: Record<IndexKey, readonly string[]> = {
  ndvi_spring: ["#1f3a14", "#2f5a1f", "#4f9a2f", "#7cc95a", "#9fe870", "#d4f7b8"],
  ndmi_summer: ["#13314a", "#1d4f73", "#2c6e96", "#4a8fba", "#6cb2dd", "#a9d6f0"],
};

/** The ramp of an index in the light or dark theme. */
export function rampOf(index: IndexKey, dark = false): readonly string[] {
  return (dark ? RAMPS_DARK : RAMPS)[index];
}

/** Missing-data grey of the light theme (lib/theme.ts has the dark one). */
export const NO_DATA = "#e8ebe6";

/**
 * Class breaks that split the values into `classes` groups of similar size (quantiles).
 * Computed once over every campaign, so the same colour means the same value in every year.
 */
export function quantileBreaks(values: readonly number[], classes: number): number[] {
  const sorted = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (sorted.length === 0 || classes < 2) return [];
  const breaks: number[] = [];
  for (let i = 1; i < classes; i++) {
    const position = (sorted.length - 1) * (i / classes);
    const low = Math.floor(position);
    const high = Math.ceil(position);
    const value = sorted[low] + (sorted[high] - sorted[low]) * (position - low);
    breaks.push(Math.round(value * 1000) / 1000);
  }
  return breaks;
}

/** Index of the class a value falls in, given ascending breaks (null for missing data). */
export function classOf(
  value: number | null | undefined,
  breaks: readonly number[],
): number | null {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  let index = 0;
  while (index < breaks.length && value >= breaks[index]) index++;
  return index;
}

export function colourOf(
  value: number | null | undefined,
  breaks: readonly number[],
  ramp: readonly string[],
  noData: string = NO_DATA,
): string {
  const index = classOf(value, breaks);
  return index === null ? noData : ramp[index];
}

export type Lang = "es" | "en";

const LOCALES: Record<Lang, string> = { es: "es-ES", en: "en-GB" };

/** "392.300 t" (es) / "392,300 t" (en); thousand tonnes when `kt` is set: "392 kt". */
export function formatTonnes(value: number | null, lang: Lang, kt = false): string {
  if (value === null || !Number.isFinite(value)) return "—";
  if (kt) {
    const thousands = new Intl.NumberFormat(LOCALES[lang], {
      maximumFractionDigits: value < 100_000 ? 1 : 0,
    }).format(value / 1000);
    return `${thousands} kt`;
  }
  return `${new Intl.NumberFormat(LOCALES[lang], { maximumFractionDigits: 0, useGrouping: "always" }).format(Math.round(value / 100) * 100)} t`;
}

export function formatIndex(value: number | null | undefined, lang: Lang): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat(LOCALES[lang], {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value: number | null, lang: Lang): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${new Intl.NumberFormat(LOCALES[lang], { maximumFractionDigits: 0 }).format(value)}\u00a0%`;
}

/** Signed percentage with a real minus sign: "+20 %", "−45 %", "0 %" (no-break space). */
export function formatSignedPercent(value: number | null, lang: Lang): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value);
  const digits = new Intl.NumberFormat(LOCALES[lang], { maximumFractionDigits: 0 }).format(
    Math.abs(rounded),
  );
  const sign = rounded > 0 ? "+" : rounded < 0 ? "\u2212" : "";
  return `${sign}${digits}\u00a0%`;
}

/** Months (YYYY-MM) whose images feed campaign "Y/Y+1": October Y-1 to August Y. */
export function campaignWindow(campaign: string): { start: string; end: string } {
  const year = Number(campaign.slice(0, 4));
  return { start: `${year - 1}-10`, end: `${year}-08` };
}
