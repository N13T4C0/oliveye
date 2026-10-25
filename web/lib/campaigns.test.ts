import { describe, expect, it } from "vitest";

import { listRows, matchesSearch, provinceChartRows, sortRows } from "./campaigns";
import type { MunicipalityProperties } from "./types";

const features: MunicipalityProperties[] = [
  {
    province_code: "23",
    municipality_code: "92",
    name: "Úbeda",
    olive_ha: 30000,
    cells: 4000,
    indices: { "2025/26": { ndvi_spring: 0.39, ndvi_summer: 0.3, ndmi_summer: -0.05 } },
  },
  {
    province_code: "23",
    municipality_code: "60",
    name: "Martos",
    olive_ha: 21000,
    cells: 3130,
    indices: { "2025/26": { ndvi_spring: 0.41, ndvi_summer: 0.31, ndmi_summer: null } },
  },
  {
    province_code: "18",
    municipality_code: "104",
    name: "Loja",
    olive_ha: 9000,
    cells: 900,
    indices: {},
  },
];

describe("municipality list", () => {
  it("reads the selected index and campaign, null when missing", () => {
    const rows = listRows(features, "ndvi_spring", "2025/26");
    expect(rows.map((r) => r.value)).toEqual([0.39, 0.41, null]);
    expect(listRows(features, "ndmi_summer", "2025/26")[1].value).toBeNull();
  });

  it("sorts by value (missing last) or by name", () => {
    const rows = listRows(features, "ndvi_spring", "2025/26");
    expect(sortRows(rows, "value", "es").map((r) => r.name)).toEqual(["Martos", "Úbeda", "Loja"]);
    expect(sortRows(rows, "name", "es").map((r) => r.name)).toEqual(["Loja", "Martos", "Úbeda"]);
  });

  it("searches without caring about accents or case", () => {
    expect(matchesSearch("Úbeda", "ubeda")).toBe(true);
    expect(matchesSearch("Alcalá la Real", " ALCALA ")).toBe(true);
    expect(matchesSearch("Martos", "loja")).toBe(false);
  });
});

describe("province chart rows", () => {
  it("adds the forecast and its interval only to the forecast campaign", () => {
    const rows = provinceChartRows(
      [
        {
          campaign: "2025/26",
          oil_final_t: 389000,
          oil_aforo_t: 475000,
          pred_t: 410000,
          target_method: "derived_from_aforo",
        },
        {
          campaign: "2026/27",
          oil_final_t: null,
          oil_aforo_t: 575000,
          pred_t: null,
          target_method: null,
        },
      ],
      { campaign: "2026/27", pred_t: 392300, low_t: 196100, high_t: 784800 },
    );
    expect(rows[0].forecast).toBeNull();
    expect(rows[1]).toMatchObject({ forecast: 392300, band: [196100, 784800], aforo: 575000 });
  });
});
