import { describe, expect, it } from "vitest";

import {
  anomalyOf,
  formatEuroRange,
  formatKgPerHa,
  formatMillionLitres,
  harvestValue,
  kgPerHectare,
  tonnesToLitres,
} from "./farm";
import type { MunicipalityProperties, ReferencePrice } from "./types";

const price: ReferencePrice = {
  week_start: "2026-10-13",
  week_end: "2026-10-19",
  eur_per_kg: { virgen_extra: 3.16, virgen: 2.99, lampante: 2.88 },
  low_eur_per_kg: 2.88,
  high_eur_per_kg: 3.16,
  source: "Poolred",
  source_url: "https://example.org",
  oil_density_kg_per_l: 0.916,
};

describe("units", () => {
  it("converts tonnes of oil to litres with its density", () => {
    expect(tonnesToLitres(1)).toBeCloseTo(1091.7, 1);
    expect(formatMillionLitres(tonnesToLitres(575_000), "es")).toBe("628 millones de litros");
    expect(formatMillionLitres(tonnesToLitres(96_500), "en")).toBe("105 million litres");
  });

  it("values the harvest between the cheapest and the dearest category", () => {
    const value = harvestValue(575_000, price);
    expect(value).toEqual([1_656_000_000, 1_817_000_000]);
    expect(formatEuroRange(value, "es")).toBe("1.660–1.820 millones de €");
    expect(formatEuroRange(value, "en")).toBe("€1,660–1,820 million");
  });

  it("gives kilos of oil per hectare", () => {
    expect(kgPerHectare(575_000, 584_829)).toBeCloseTo(983.2, 1);
    expect(formatKgPerHa(983.2, "es")).toBe("980 kg/ha");
    expect(kgPerHectare(1, 0)).toBeNull();
  });
});

describe("anomalyOf", () => {
  const municipality = (values: Record<string, number | null>): MunicipalityProperties => ({
    province_code: "23",
    municipality_code: "60",
    name: "Martos",
    olive_ha: 1,
    cells: 1,
    indices: Object.fromEntries(
      Object.entries(values).map(([c, v]) => [
        c,
        { ndvi_spring: v, ndvi_summer: null, ndmi_summer: null },
      ]),
    ),
  });

  it("compares a campaign with the municipality's other campaigns only", () => {
    const m = municipality({ a: 0.4, b: 0.42, c: 0.38, d: 0.4, e: 0.3 });
    const result = anomalyOf(m, "ndvi_spring", "e");
    expect(result?.pct).toBeCloseTo(-25, 5);
    expect(result?.cls).toBe(0); // far below usual
    expect(anomalyOf(m, "ndvi_spring", "a")?.cls).toBe(2); // within its usual range
  });

  it("needs enough history and a value", () => {
    expect(anomalyOf(municipality({ a: 0.4, b: 0.4, c: 0.41 }), "ndvi_spring", "a")).toBeNull();
    expect(
      anomalyOf(municipality({ a: null, b: 0.4, c: 0.41, d: 0.4, e: 0.42 }), "ndvi_spring", "a"),
    ).toBeNull();
  });
});
