/** Shapes returned by the OlivEye API (api/oliveye_api.py). Keep in sync with its models. */

export type ProvinceName = "Jaén" | "Granada";

export interface Municipality {
  province_code: string;
  municipality_code: string;
  name: string;
  olive_hectares: number;
  processed: boolean;
}

export interface MonthlyIndex {
  month: string; // "2025-07"
  ndvi: number | null;
  ndmi: number | null;
  valid_cells: number | null;
}

export interface ProductionPoint {
  campaign: string; // "2025/26"
  oil_final_t: number | null;
  oil_aforo_t: number | null;
  pred_t: number | null;
  target_method: string | null;
}

export interface ModelScore {
  model: string;
  rows: number;
  campaigns: number;
  mape_pct: number | null;
  campaign_wins_vs_aforo: number;
  p_vs_aforo: number | null;
}

export interface ForecastRow {
  province: ProvinceName;
  pred_t: number;
  low_t: number;
  high_t: number;
  oil_aforo_t: number | null;
}

export interface Forecast {
  campaign: string;
  published: string;
  interval_factor: number;
  rows: ForecastRow[];
}

/** Seasonal indices of one municipality in one campaign (data up to August). */
export interface SeasonalIndices {
  ndvi_spring: number | null;
  ndvi_summer: number | null;
  ndmi_summer: number | null;
}

export interface MunicipalityProperties {
  province_code: string;
  municipality_code: string;
  name: string;
  olive_ha: number;
  cells: number;
  indices: Record<string, SeasonalIndices>;
}

export type IndexKey = "ndvi_spring" | "ndmi_summer";

/** Dated Poolred origin price per oil category (GET /prices/reference). */
export interface ReferencePrice {
  week_start: string;
  week_end: string;
  eur_per_kg: Record<string, number>;
  low_eur_per_kg: number;
  high_eur_per_kg: number;
  source: string;
  source_url: string;
  oil_density_kg_per_l: number;
}

export interface PageData {
  municipalities: Municipality[];
  production: Record<ProvinceName, ProductionPoint[]>;
  summary: ModelScore[];
  forecast: Forecast;
  /** Null when the API has no price yet: the page then shows litres only. */
  price: ReferencePrice | null;
}
