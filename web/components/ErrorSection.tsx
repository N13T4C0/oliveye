"use client";

import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";

import { campaignErrors, summariseErrors, type CampaignError, type Closer } from "@/lib/errors";
import { t } from "@/lib/i18n";
import { formatPercent, formatSignedPercent, formatTonnes, type Lang } from "@/lib/scale";
import { chartColours, useTheme } from "@/lib/theme";
import type { ModelScore, ProductionPoint, ProvinceName } from "@/lib/types";

import layout from "./ChartSection.module.css";
import styles from "./ErrorSection.module.css";

const PROVINCES: ProvinceName[] = ["Jaén", "Granada"];

interface Props {
  lang: Lang;
  campaign: string;
  production: Record<ProvinceName, ProductionPoint[]>;
  /** Published scores, for the naive "last campaign" baseline next to OlivEye and the aforo. */
  scores: ModelScore[];
}

const isDerived = (row: CampaignError) => row.targetMethod === "derived_from_aforo";

/**
 * Campaign by campaign: how far OlivEye and the aforo were from the final production.
 * Bars above zero over-estimated the harvest, bars below under-estimated it.
 */
export function ErrorSection({ lang, campaign, production, scores }: Props) {
  const [showTable, setShowTable] = useState(false);
  const rows = useMemo(() => campaignErrors(production), [production]);
  const summary = summariseErrors(rows);
  // One scale for both provinces, so a bar of the same height means the same error.
  const values = rows.flatMap((r) => [r.oliveyePct, r.aforoPct ?? 0]);
  const domain: [number, number] = [
    Math.min(-50, Math.floor(Math.min(...values) / 50) * 50),
    Math.max(50, Math.ceil(Math.max(...values) / 50) * 50),
  ];

  return (
    <section className={layout.section} aria-labelledby="errors-title">
      <div className={layout.inner}>
        <header className={layout.head}>
          <h2 id="errors-title" className={layout.title}>
            {t(lang, "errorsTitle")}
          </h2>
          <p className={layout.lead}>{t(lang, "errorsLead")}</p>
        </header>

        <p className={styles.summary}>
          {t(lang, "errorsSummary", {
            n: summary.oliveyeCloser,
            total: summary.rows,
            model: formatPercent(summary.oliveyeMape, lang),
            aforo: formatPercent(summary.aforoMape, lang),
            last: formatPercent(
              scores.find((s) => s.model === "last_campaign")?.mape_pct ?? null,
              lang,
            ),
          })}
        </p>

        <ul className={layout.key} aria-label={lang === "es" ? "Leyenda" : "Legend"}>
          <li>
            <span className={`${layout.mark} ${styles.markModel}`} aria-hidden="true" />
            {t(lang, "oliveye")}
          </li>
          <li>
            <span className={`${layout.mark} ${styles.markAforo}`} aria-hidden="true" />
            {t(lang, "aforo")}
          </li>
        </ul>

        <div className={layout.panels}>
          {PROVINCES.map((province) => (
            <ErrorPanel
              key={province}
              lang={lang}
              province={province}
              campaign={campaign}
              domain={domain}
              rows={rows.filter((r) => r.province === province)}
            />
          ))}
        </div>

        <p className={layout.note}>{t(lang, "errorsNote")}</p>

        <button
          type="button"
          className={layout.tableToggle}
          aria-expanded={showTable}
          onClick={() => setShowTable((v) => !v)}
        >
          {t(lang, showTable ? "hideTable" : "showTable")}
        </button>
        {showTable && <ErrorTable lang={lang} rows={rows} />}
      </div>
    </section>
  );
}

function ErrorPanel({
  lang,
  province,
  campaign,
  domain,
  rows,
}: {
  lang: Lang;
  province: ProvinceName;
  campaign: string;
  domain: [number, number];
  rows: CampaignError[];
}) {
  const [theme] = useTheme();
  const c = chartColours(theme);
  const inRange = rows.some((r) => r.campaign === campaign);

  return (
    <figure className={layout.panel}>
      <figcaption className={layout.panelTitle}>{province}</figcaption>
      <div className={layout.chart}>
        <BarChart
          responsive
          data={rows}
          style={{ width: "100%", height: "100%" }}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
          barGap={2}
          barCategoryGap="22%"
        >
          <CartesianGrid vertical={false} stroke={c.grid} />
          {inRange && (
            <ReferenceLine
              x={campaign}
              stroke={c.highlight}
              strokeOpacity={0.3}
              strokeWidth={30}
              ifOverflow="hidden"
            />
          )}
          <XAxis
            dataKey="campaign"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: c.tick }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={64}
            tick={{ fontSize: 11, fill: c.tick }}
            domain={domain}
            ticks={ticksFor(domain)}
            tickFormatter={(v: number) => formatSignedPercent(v, lang)}
          />
          <ReferenceLine y={0} stroke={c.real} strokeWidth={1} />
          <Tooltip
            cursor={{ fill: c.grid, fillOpacity: 0.5 }}
            content={({ active, payload }) => (
              <ErrorTooltip active={active} payload={payload} lang={lang} />
            )}
          />
          <Bar
            name={t(lang, "oliveye")}
            dataKey="oliveyePct"
            fill={c.oliveye}
            radius={2}
            isAnimationActive={false}
          />
          <Bar
            name={t(lang, "aforo")}
            dataKey="aforoPct"
            fill={c.aforo}
            radius={2}
            isAnimationActive={false}
          />
        </BarChart>
      </div>
    </figure>
  );
}

/** Ticks every 50 points inside the domain, zero included. */
function ticksFor([low, high]: [number, number]): number[] {
  const ticks: number[] = [];
  for (let v = low; v <= high; v += 50) ticks.push(v);
  return ticks;
}

interface TooltipProps {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: unknown }>;
  lang: Lang;
}

function ErrorTooltip({ active, payload, lang }: TooltipProps) {
  const row = payload?.[0]?.payload as CampaignError | undefined;
  if (!active || !row) return null;
  return (
    <div className={styles.tooltip}>
      <strong>
        {row.province} · {row.campaign}
      </strong>
      <span className="num">
        {t(lang, "real")}: {formatTonnes(row.finalT, lang)}
        {isDerived(row) && ` (${t(lang, "derivedMark")})`}
      </span>
      <span className="num">
        {t(lang, "oliveye")}: {formatSignedPercent(row.oliveyePct, lang)}
      </span>
      <span className="num">
        {t(lang, "aforo")}:{" "}
        {row.aforoPct === null ? t(lang, "noAforo") : formatSignedPercent(row.aforoPct, lang)}
      </span>
      {row.closer && <span className={styles.closer}>{closerLabel(row.closer, lang)}</span>}
    </div>
  );
}

/** "Más cerca: OlivEye" in the tooltip, just "OlivEye" in the table's "closer" column. */
function closerLabel(closer: Closer | null, lang: Lang, short = false): string {
  if (closer === null) return t(lang, "noAforo");
  if (closer === "tie") return t(lang, "closerTie");
  return short ? t(lang, closer) : t(lang, "closer", { who: t(lang, closer) });
}

function ErrorTable({ lang, rows }: { lang: Lang; rows: CampaignError[] }) {
  return (
    <div className={layout.tableWrap}>
      <table className={layout.table}>
        <caption className="visually-hidden">{t(lang, "errorsTitle")}</caption>
        <thead>
          <tr>
            <th scope="col">{lang === "es" ? "Provincia" : "Province"}</th>
            <th scope="col">{t(lang, "campaign")}</th>
            <th scope="col">{t(lang, "real")} (t)</th>
            <th scope="col">{t(lang, "oliveye")}</th>
            <th scope="col">{t(lang, "aforo")}</th>
            <th scope="col">{t(lang, "closerColumn")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.province}-${r.campaign}`}>
              <th scope="row">{r.province}</th>
              <td className="num">{r.campaign}</td>
              <td className="num">
                {formatTonnes(r.finalT, lang)}
                {isDerived(r) ? " †" : ""}
              </td>
              <td className="num">{formatSignedPercent(r.oliveyePct, lang)}</td>
              <td className="num">
                {r.aforoPct === null ? "—" : formatSignedPercent(r.aforoPct, lang)}
              </td>
              <td>{closerLabel(r.closer, lang, true)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
