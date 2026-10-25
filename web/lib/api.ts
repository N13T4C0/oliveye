/**
 * OlivEye API client. The API is public and read-only, so one URL serves both the server
 * (page data, revalidated daily) and the browser (map GeoJSON and per-municipality series).
 */

import type {
  Forecast,
  ModelScore,
  MonthlyIndex,
  Municipality,
  PageData,
  ProductionPoint,
  ProvinceName,
  ReferencePrice,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

/** The data changes once per campaign: rebuild the page at most once a day. */
const REVALIDATE_SECONDS = 86_400;

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) throw new Error(`OlivEye API ${path} answered ${response.status}`);
  return (await response.json()) as T;
}

/** Everything the page renders on the server. */
export async function getPageData(): Promise<PageData> {
  const cached = { next: { revalidate: REVALIDATE_SECONDS } };
  const [municipalities, jaen, granada, summary, forecast] = await Promise.all([
    getJson<Municipality[]>("/municipalities", cached),
    getJson<ProductionPoint[]>(`/provinces/${encodeURIComponent("Jaén")}/production`, cached),
    getJson<ProductionPoint[]>("/provinces/Granada/production", cached),
    getJson<ModelScore[]>("/models/summary", cached),
    getJson<Forecast>("/forecast", cached),
  ]);
  const production: Record<ProvinceName, ProductionPoint[]> = { Jaén: jaen, Granada: granada };
  // Optional: without a published price the page shows litres and kg/ha only.
  const price = await getJson<ReferencePrice>("/prices/reference", cached).catch(() => null);
  return { municipalities, production, summary, forecast, price };
}

export const MAP_URL = `${API_URL}/map/municipalities`;

export function getMunicipalitySeries(
  provinceCode: string,
  municipalityCode: string,
  signal?: AbortSignal,
): Promise<MonthlyIndex[]> {
  return getJson<MonthlyIndex[]>(`/municipalities/${provinceCode}/${municipalityCode}/indices`, {
    signal,
  });
}
