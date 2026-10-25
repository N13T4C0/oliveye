/**
 * Per-campaign errors of OlivEye and the official aforo against the final production.
 *
 * Every OlivEye estimate in the production series was made leave-one-campaign-out (the model
 * never saw that campaign nor the next one), so these errors are honest out-of-sample errors.
 * The headline compares both only on "like-for-like" rows: campaigns with an OlivEye estimate,
 * an aforo and a final figure, the same rows as the published MAPE.
 */

import type { ProductionPoint, ProvinceName } from "./types";

export type Closer = "oliveye" | "aforo" | "tie";

export interface CampaignError {
  province: ProvinceName;
  campaign: string;
  finalT: number;
  oliveyeT: number;
  aforoT: number | null;
  /** Signed error in % of the final production: +20 means 20 % above what was harvested. */
  oliveyePct: number;
  aforoPct: number | null;
  /** Which estimate was nearer the final figure; null when there is no aforo to compare. */
  closer: Closer | null;
  /** True when the row has both estimates, i.e. it counts in the like-for-like comparison. */
  likeForLike: boolean;
  /** How the final figure was obtained ("reported", "derived_from_aforo", ...). */
  targetMethod: string | null;
}

/** Signed percentage error of `estimate` against `actual`. */
export function signedPct(estimate: number, actual: number): number {
  return (100 * (estimate - actual)) / actual;
}

/** Rows with an OlivEye estimate and a final figure, in campaign order per province. */
export function campaignErrors(
  production: Record<ProvinceName, readonly ProductionPoint[]>,
): CampaignError[] {
  const rows: CampaignError[] = [];
  for (const province of Object.keys(production) as ProvinceName[]) {
    for (const point of production[province]) {
      const { oil_final_t: finalT, pred_t: oliveyeT, oil_aforo_t: aforoT } = point;
      if (finalT === null || oliveyeT === null || finalT <= 0) continue;
      const oliveyePct = signedPct(oliveyeT, finalT);
      const aforoPct = aforoT === null ? null : signedPct(aforoT, finalT);
      let closer: Closer | null = null;
      if (aforoPct !== null) {
        const gap = Math.abs(oliveyePct) - Math.abs(aforoPct);
        closer = gap < 0 ? "oliveye" : gap > 0 ? "aforo" : "tie";
      }
      rows.push({
        province,
        campaign: point.campaign,
        finalT,
        oliveyeT,
        aforoT,
        oliveyePct,
        aforoPct,
        closer,
        likeForLike: aforoPct !== null,
        targetMethod: point.target_method,
      });
    }
  }
  return rows.sort(
    (a, b) => a.province.localeCompare(b.province) || a.campaign.localeCompare(b.campaign),
  );
}

export interface ErrorSummary {
  rows: number;
  oliveyeMape: number | null;
  aforoMape: number | null;
  oliveyeCloser: number;
}

/** Mean absolute % error of both estimates over the like-for-like rows only. */
export function summariseErrors(rows: readonly CampaignError[]): ErrorSummary {
  const common = rows.filter((r) => r.likeForLike);
  const mean = (values: number[]) =>
    values.length === 0 ? null : values.reduce((sum, v) => sum + v, 0) / values.length;
  return {
    rows: common.length,
    oliveyeMape: mean(common.map((r) => Math.abs(r.oliveyePct))),
    aforoMape: mean(common.map((r) => Math.abs(r.aforoPct ?? 0))),
    oliveyeCloser: common.filter((r) => r.closer === "oliveye").length,
  };
}
