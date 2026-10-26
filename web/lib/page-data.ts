/**
 * Page data, fetched on the server only (Server Component in app/page.tsx). Kept apart from
 * lib/api.ts, which client components also import, because "use cache" is server-only.
 */

import { cacheLife } from "next/cache";

import { getJson } from "./api";
import type {
  Forecast,
  ModelScore,
  Municipality,
  PageData,
  ProductionPoint,
  ProvinceName,
  ReferencePrice,
} from "./types";

/** The data changes once per campaign: rebuild the page at most once a day. */
const REVALIDATE_SECONDS = 86_400;

/**
 * Optional data: without a published price the page shows litres and kg/ha only.
 *
 * Cached with "use cache" so that a failed request (e.g. the API not yet redeployed with
 * /prices/reference, a 404) still caches its `null` instead of making the whole page dynamic,
 * which fails the static build under Cache Components. Retried every hour.
 */
async function getReferencePrice(): Promise<ReferencePrice | null> {
  "use cache";
  cacheLife("hours");
  try {
    return await getJson<ReferencePrice>("/prices/reference");
  } catch {
    return null;
  }
}

/** Everything the page renders on the server. */
export async function getPageData(): Promise<PageData> {
  const cached = { next: { revalidate: REVALIDATE_SECONDS } };
  const [municipalities, jaen, granada, summary, forecast, price] = await Promise.all([
    getJson<Municipality[]>("/municipalities", cached),
    getJson<ProductionPoint[]>(`/provinces/${encodeURIComponent("Jaén")}/production`, cached),
    getJson<ProductionPoint[]>("/provinces/Granada/production", cached),
    getJson<ModelScore[]>("/models/summary", cached),
    getJson<Forecast>("/forecast", cached),
    getReferencePrice(),
  ]);
  const production: Record<ProvinceName, ProductionPoint[]> = { Jaén: jaen, Granada: granada };
  return { municipalities, production, summary, forecast, price };
}
