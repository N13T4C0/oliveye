import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { campaignErrors, signedPct, summariseErrors } from "./errors";
import type { ModelScore, ProductionPoint, ProvinceName } from "./types";

const point = (campaign: string, real: number | null, aforo: number | null, pred: number | null) =>
  ({
    campaign,
    oil_final_t: real,
    oil_aforo_t: aforo,
    pred_t: pred,
    target_method: "derived_from_aforo",
  }) satisfies ProductionPoint;

describe("signedPct", () => {
  it("is positive when the estimate is above the harvest", () => {
    expect(signedPct(120, 100)).toBe(20);
    expect(signedPct(80, 100)).toBe(-20);
  });
});

describe("campaignErrors", () => {
  const production: Record<ProvinceName, ProductionPoint[]> = {
    Jaén: [
      point("2016/17", 500, 540, null), // no OlivEye estimate: left out
      point("2017/18", 400, 360, 380), // OlivEye -5 %, aforo -10 %
      point("2026/27", null, 575, null), // future campaign: left out
    ],
    Granada: [
      point("2019/20", 100, null, 90), // no aforo: shown, but not like-for-like
      point("2020/21", 100, 98, 70), // aforo closer
    ],
  };

  it("keeps rows with an estimate and a final figure, sorted by province and campaign", () => {
    const rows = campaignErrors(production);
    expect(rows.map((r) => `${r.province} ${r.campaign}`)).toEqual([
      "Granada 2019/20",
      "Granada 2020/21",
      "Jaén 2017/18",
    ]);
  });

  it("says which estimate was closer, and only when both exist", () => {
    const rows = campaignErrors(production);
    expect(rows.map((r) => r.closer)).toEqual([null, "aforo", "oliveye"]);
    expect(rows.map((r) => r.likeForLike)).toEqual([false, true, true]);
  });

  it("summarises like-for-like rows only", () => {
    const summary = summariseErrors(campaignErrors(production));
    expect(summary.rows).toBe(2);
    expect(summary.oliveyeMape).toBeCloseTo((30 + 5) / 2);
    expect(summary.aforoMape).toBeCloseTo((2 + 10) / 2);
    expect(summary.oliveyeCloser).toBe(1);
  });
});

describe("published data", () => {
  // The web recomputes errors from the production series; they must match the published MAPE.
  const data = join(__dirname, "..", "..", "api", "data");
  const production = JSON.parse(readFileSync(join(data, "production.json"), "utf8")) as Record<
    ProvinceName,
    ProductionPoint[]
  >;
  const scores = JSON.parse(readFileSync(join(data, "summary.json"), "utf8")) as ModelScore[];
  const score = (model: string) => scores.find((s) => s.model === model)?.mape_pct;

  it("reproduces the like-for-like MAPE of OlivEye (Ridge) and the aforo", () => {
    const summary = summariseErrors(campaignErrors(production));
    expect(summary.rows).toBe(scores[0].rows);
    expect(Number(summary.oliveyeMape?.toFixed(1))).toBe(score("ridge"));
    expect(Number(summary.aforoMape?.toFixed(1))).toBe(score("aforo"));
  });
});
