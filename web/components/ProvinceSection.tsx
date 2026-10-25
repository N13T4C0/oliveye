"use client";

import { useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  ErrorBar,
  Line,
  ReferenceLine,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { provinceChartRows, type ProvinceChartRow } from "@/lib/campaigns";
import { t } from "@/lib/i18n";
import { formatTonnes, type Lang } from "@/lib/scale";
import type { Forecast, ProductionPoint, ProvinceName } from "@/lib/types";

import styles from "./ProvinceSection.module.css";

const PROVINCES: ProvinceName[] = ["Jaén", "Granada"];

interface Props {
  lang: Lang;
  campaign: string;
  production: Record<ProvinceName, ProductionPoint[]>;
  forecast: Forecast;
}

/** Real production, aforo and OlivEye per campaign, one panel per province (own y-axis). */
export function ProvinceSection({ lang, campaign, production, forecast }: Props) {
  const [showTable, setShowTable] = useState(false);

  return (
    <section className={styles.section} aria-labelledby="provinces-title">
      <div className={styles.inner}>
        <header className={styles.head}>
          <h2 id="provinces-title" className={styles.title}>
            {t(lang, "provincesTitle")}
          </h2>
          <p className={styles.lead}>{t(lang, "provincesLead")}</p>
        </header>

        <ul className={styles.key} aria-label={lang === "es" ? "Leyenda" : "Legend"}>
          <li>
            <span className={`${styles.mark} ${styles.markReal}`} aria-hidden="true" />
            {t(lang, "real")}
          </li>
          <li>
            <span className={`${styles.mark} ${styles.markAforo}`} aria-hidden="true" />
            {t(lang, "aforo")}
          </li>
          <li>
            <span className={`${styles.mark} ${styles.markModel}`} aria-hidden="true" />
            {t(lang, "oliveye")}
          </li>
          <li>
            <span className={`${styles.mark} ${styles.markForecast}`} aria-hidden="true" />
            {t(lang, "forecast")} · {t(lang, "interval")}
          </li>
          <li>
            <span className={`${styles.mark} ${styles.markSelected}`} aria-hidden="true" />
            {t(lang, "selectedCampaign")} ({campaign})
          </li>
        </ul>

        <div className={styles.panels}>
          {PROVINCES.map((province) => {
            const row = forecast.rows.find((r) => r.province === province);
            const rows = provinceChartRows(
              production[province],
              row ? { campaign: forecast.campaign, ...row } : undefined,
            );
            return (
              <ProvincePanel
                key={province}
                lang={lang}
                province={province}
                campaign={campaign}
                rows={rows}
              />
            );
          })}
        </div>

        <p className={styles.note}>
          {t(lang, "derivedNote")} {lang === "es" ? "Fuente:" : "Source:"} Junta de Andalucía
          (aforos), AICA.
        </p>

        <button
          type="button"
          className={styles.tableToggle}
          aria-expanded={showTable}
          onClick={() => setShowTable((v) => !v)}
        >
          {t(lang, showTable ? "hideTable" : "showTable")}
        </button>
        {showTable && <ProductionTable lang={lang} production={production} forecast={forecast} />}
      </div>
    </section>
  );
}

function ProvincePanel({
  lang,
  province,
  campaign,
  rows,
}: {
  lang: Lang;
  province: ProvinceName;
  campaign: string;
  rows: ProvinceChartRow[];
}) {
  // ErrorBar expects distances from the point, not absolute limits.
  const data = rows.map((r) => ({
    ...r,
    bandError:
      r.band && r.forecast !== null ? [r.forecast - r.band[0], r.band[1] - r.forecast] : undefined,
  }));
  const inRange = rows.some((r) => r.campaign === campaign);

  return (
    <figure className={styles.panel}>
      <figcaption className={styles.panelTitle}>{province}</figcaption>
      <div className={styles.chart}>
        <ComposedChart
          responsive
          data={data}
          style={{ width: "100%", height: "100%" }}
          margin={{ top: 8, right: 12, bottom: 0, left: 4 }}
        >
          <CartesianGrid vertical={false} stroke="#e8ebe6" />
          {inRange && (
            <ReferenceLine
              x={campaign}
              stroke="#9fe870"
              strokeOpacity={0.3}
              strokeWidth={22}
              ifOverflow="hidden"
            />
          )}
          <XAxis
            dataKey="campaign"
            tickLine={false}
            axisLine={{ stroke: "#d6dad3" }}
            tick={{ fontSize: 11, fill: "#6a6c6a" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={56}
            tick={{ fontSize: 11, fill: "#6a6c6a" }}
            tickFormatter={(v: number) => formatTonnes(v, lang, true)}
            domain={[0, "auto"]}
          />
          <Tooltip
            contentStyle={{ borderRadius: 10, border: "1px solid #d6dad3", fontSize: 13 }}
            formatter={(value, name) => [
              typeof value === "number" ? formatTonnes(value, lang) : "—",
              String(name),
            ]}
          />
          <Line
            name={t(lang, "aforo")}
            dataKey="aforo"
            stroke="#0b4c72"
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={{ r: 3, fill: "#0b4c72", strokeWidth: 0 }}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            name={t(lang, "oliveye")}
            dataKey="oliveye"
            stroke="#054d28"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#054d28", strokeWidth: 0 }}
            isAnimationActive={false}
          />
          <Line
            name={t(lang, "real")}
            dataKey="real"
            stroke="#0e0f0c"
            strokeWidth={1}
            dot={{ r: 4.5, fill: "#0e0f0c", stroke: "#ffffff", strokeWidth: 1.5 }}
            isAnimationActive={false}
          />
          <Scatter
            name={t(lang, "forecast")}
            dataKey="forecast"
            fill="#054d28"
            shape="diamond"
            isAnimationActive={false}
          >
            <ErrorBar
              dataKey="bandError"
              width={10}
              stroke="#054d28"
              strokeWidth={1.5}
              direction="y"
            />
          </Scatter>
        </ComposedChart>
      </div>
    </figure>
  );
}

function ProductionTable({
  lang,
  production,
  forecast,
}: {
  lang: Lang;
  production: Record<ProvinceName, ProductionPoint[]>;
  forecast: Forecast;
}) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <caption className="visually-hidden">{t(lang, "provincesTitle")}</caption>
        <thead>
          <tr>
            <th scope="col">{lang === "es" ? "Provincia" : "Province"}</th>
            <th scope="col">{t(lang, "campaign")}</th>
            <th scope="col">{t(lang, "real")} (t)</th>
            <th scope="col">{t(lang, "aforo")} (t)</th>
            <th scope="col">{t(lang, "oliveye")} (t)</th>
          </tr>
        </thead>
        <tbody>
          {PROVINCES.flatMap((province) =>
            production[province].map((p) => {
              const f =
                p.campaign === forecast.campaign
                  ? forecast.rows.find((r) => r.province === province)
                  : undefined;
              return (
                <tr key={`${province}-${p.campaign}`}>
                  <th scope="row">{province}</th>
                  <td className="num">{p.campaign}</td>
                  <td className="num">{formatTonnes(p.oil_final_t, lang)}</td>
                  <td className="num">{formatTonnes(p.oil_aforo_t, lang)}</td>
                  <td className="num">
                    {f
                      ? `${formatTonnes(f.pred_t, lang)} (${formatTonnes(f.low_t, lang, true)}–${formatTonnes(f.high_t, lang, true)})`
                      : formatTonnes(p.pred_t, lang)}
                  </td>
                </tr>
              );
            }),
          )}
        </tbody>
      </table>
    </div>
  );
}
