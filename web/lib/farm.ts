/**
 * Plain-language helpers for the default ("simple") view: litres, euros, kilos per hectare, and
 * each municipality compared with its own usual values instead of raw NDVI/NDMI numbers.
 */

import type { Lang } from "./scale";
import type { IndexKey, MunicipalityProperties, ReferencePrice } from "./types";

const LOCALES: Record<Lang, string> = { es: "es-ES", en: "en-GB" };

/** Olive oil weighs about 0.916 kg per litre, so one tonne is about 1,092 litres. */
export const DEFAULT_DENSITY_KG_PER_L = 0.916;

export function tonnesToLitres(tonnes: number, densityKgPerL = DEFAULT_DENSITY_KG_PER_L): number {
  return (tonnes * 1000) / densityKgPerL;
}

/** Value range of a harvest: tonnes x the lowest and highest category price of one week. */
export function harvestValue(tonnes: number, price: ReferencePrice): [number, number] {
  return [tonnes * 1000 * price.low_eur_per_kg, tonnes * 1000 * price.high_eur_per_kg];
}

export function kgPerHectare(tonnes: number, hectares: number): number | null {
  return hectares > 0 ? (tonnes * 1000) / hectares : null;
}

/** "625 millones de litros" / "625 million litres". */
export function formatMillionLitres(litres: number | null, lang: Lang): string {
  if (litres === null || !Number.isFinite(litres)) return "—";
  const millions = new Intl.NumberFormat(LOCALES[lang], {
    maximumFractionDigits: litres < 100e6 ? 1 : 0,
  }).format(litres / 1e6);
  return lang === "es" ? `${millions} millones de litros` : `${millions} million litres`;
}

/** "1.660–1.820 millones de €" / "€1,660–1,820 million". */
export function formatEuroRange([low, high]: [number, number], lang: Lang): string {
  const f = new Intl.NumberFormat(LOCALES[lang], {
    maximumFractionDigits: 0,
    useGrouping: "always",
  });
  const round = (v: number) => Math.round(v / 1e7) * 10; // nearest 10 million, in millions
  return lang === "es"
    ? `${f.format(round(low))}–${f.format(round(high))} millones de €`
    : `€${f.format(round(low))}–${f.format(round(high))} million`;
}

export function formatKgPerHa(value: number | null, lang: Lang): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const f = new Intl.NumberFormat(LOCALES[lang], {
    maximumFractionDigits: 0,
    useGrouping: "always",
  });
  return `${f.format(Math.round(value / 10) * 10)} kg/ha`;
}

// --------------------------------------------------------------------------------------------
// Compared with its usual values
// --------------------------------------------------------------------------------------------

/**
 * Five classes from "much below usual" to "much above usual", by how many standard deviations a
 * campaign is from the same municipality's other campaigns (a z-score). ±0.5 and ±1.5 put about
 * a third of the campaigns in "usual" and only clear exceptions in the outer classes.
 */
export const ANOMALY_BREAKS = [-1.5, -0.5, 0.5, 1.5] as const;
export type AnomalyClass = 0 | 1 | 2 | 3 | 4;

/** Fewer other campaigns than this and "usual" is not known well enough to compare with. */
const MIN_OTHER_CAMPAIGNS = 4;

export interface Anomaly {
  /** Standard deviations from the municipality's other campaigns. */
  z: number;
  /** Difference from the mean of the other campaigns, in % of that mean. */
  pct: number;
  cls: AnomalyClass;
}

/** One campaign against the municipality's other campaigns (leave-one-out, so it never compares with itself). */
export function anomalyOf(
  municipality: MunicipalityProperties,
  index: IndexKey,
  campaign: string,
): Anomaly | null {
  const value = municipality.indices[campaign]?.[index];
  if (value === null || value === undefined) return null;
  const others = Object.entries(municipality.indices)
    .filter(([c]) => c !== campaign)
    .map(([, v]) => v[index])
    .filter((v): v is number => v !== null && Number.isFinite(v));
  if (others.length < MIN_OTHER_CAMPAIGNS) return null;
  const mean = others.reduce((s, v) => s + v, 0) / others.length;
  const sd = Math.sqrt(others.reduce((s, v) => s + (v - mean) ** 2, 0) / (others.length - 1));
  if (!(sd > 0)) return null;
  const z = (value - mean) / sd;
  let cls = 0;
  while (cls < ANOMALY_BREAKS.length && z >= ANOMALY_BREAKS[cls]) cls++;
  return { z, pct: (100 * (value - mean)) / Math.abs(mean), cls: cls as AnomalyClass };
}

/**
 * Diverging palettes (ColorBrewer BrBG and RdBu, colour-blind safe), from class 0 to 4.
 * Greenness: brown (less green) → neutral → teal (greener).
 * Thirst uses NDMI, where a LOW value means MORE thirst: class 0 (very low NDMI) is red.
 */
export const ANOMALY_RAMPS: Record<IndexKey, readonly string[]> = {
  ndvi_spring: ["#8c510a", "#d8b365", "#ece6d8", "#5ab4ac", "#01665e"],
  ndmi_summer: ["#b2182b", "#ef8a62", "#ece6d8", "#67a9cf", "#2166ac"],
};

/**
 * Below this many 250 m cells (about 300 ha of pure olive grove) a municipality's figure rests on
 * a small sample: one new plantation or a change in irrigation can move it a lot (Cúllar, 22
 * cells, went from NDVI 0.17 to 0.32 in two years). The page says so next to the figure.
 */
export const SMALL_SAMPLE_CELLS = 50;
