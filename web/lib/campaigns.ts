/** Campaign helpers shared by the map, the list and the province chart. */

import type { MunicipalityProperties, ProductionPoint, IndexKey } from "./types";

/** Campaigns with satellite indices (data from October 2016 to September 2026). */
export const INDEX_CAMPAIGNS = [
  "2017/18",
  "2018/19",
  "2019/20",
  "2020/21",
  "2021/22",
  "2022/23",
  "2023/24",
  "2024/25",
  "2025/26",
  "2026/27",
] as const;

export type Campaign = (typeof INDEX_CAMPAIGNS)[number];

/** The forecast campaign is the default: it is the one people are asking about now. */
export const DEFAULT_CAMPAIGN: Campaign = "2026/27";

/** Flat property key used by the map's paint expressions, e.g. "ndvi_spring|2025/26". */
export function indexProperty(index: IndexKey, campaign: string): string {
  return `${index}|${campaign}`;
}

export interface ListRow {
  id: string; // "23-60"
  provinceCode: string;
  municipalityCode: string;
  name: string;
  oliveHa: number;
  value: number | null;
}

export function listRows(
  features: readonly MunicipalityProperties[],
  index: IndexKey,
  campaign: string,
): ListRow[] {
  return features.map((p) => ({
    id: `${p.province_code}-${p.municipality_code}`,
    provinceCode: p.province_code,
    municipalityCode: p.municipality_code,
    name: p.name,
    oliveHa: p.olive_ha,
    value: p.indices[campaign]?.[index] ?? null,
  }));
}

/** Case- and accent-insensitive match ("ubeda" finds "Úbeda"). */
export function matchesSearch(name: string, query: string): boolean {
  const fold = (s: string) =>
    s
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLowerCase();
  return fold(name).includes(fold(query.trim()));
}

export type SortMode = "value" | "name";

export function sortRows(rows: readonly ListRow[], mode: SortMode, lang: string): ListRow[] {
  const byName = (a: ListRow, b: ListRow) => a.name.localeCompare(b.name, lang);
  return [...rows].sort((a, b) => {
    if (mode === "name") return byName(a, b);
    if (a.value === null && b.value === null) return byName(a, b);
    if (a.value === null) return 1;
    if (b.value === null) return -1;
    return b.value - a.value || byName(a, b);
  });
}

/** Rows for the province chart: one per campaign, the forecast campaign included. */
export interface ProvinceChartRow {
  campaign: string;
  real: number | null;
  aforo: number | null;
  oliveye: number | null;
  forecast: number | null;
  band: [number, number] | null;
}

export function provinceChartRows(
  series: readonly ProductionPoint[],
  forecast: { campaign: string; pred_t: number; low_t: number; high_t: number } | undefined,
): ProvinceChartRow[] {
  return series.map((point) => {
    const isForecast = forecast !== undefined && point.campaign === forecast.campaign;
    return {
      campaign: point.campaign,
      real: point.oil_final_t,
      aforo: point.oil_aforo_t,
      oliveye: point.pred_t,
      forecast: isForecast ? forecast.pred_t : null,
      band: isForecast ? [forecast.low_t, forecast.high_t] : null,
    };
  });
}
