/**
 * OlivEye API client. The API is public and read-only, so one URL serves both the server
 * (page data, revalidated daily) and the browser (map GeoJSON and per-municipality series).
 */

import type { MonthlyIndex } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) throw new Error(`OlivEye API ${path} answered ${response.status}`);
  return (await response.json()) as T;
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
