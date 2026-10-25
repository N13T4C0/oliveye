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
import { chartColours, useTheme } from "@/lib/theme";
import type { Forecast, ProductionPoint, ProvinceName } from "@/lib/types";

import layout from "./ChartSection.module.css";
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
    <section className={layout.section} aria-labelledby="provinces-title">
      <div className={layout.inner}>
        <header className={layout.head}>
          <h2 id="provinces-title" className={layout.title}>
            {t(lang, "provincesTitle")}
          </h2>
          <p className={layout.lead}>{t(lang, "provincesLead")}</p>
        </header>

        <ul className={layout.key} aria-label={lang === "es" ? "Leyenda" : "Legend"}>
          <li>
            <span className={`${layout.mark} ${styles.markReal}`} aria-hidden="true" />
            {t(lang, "real")}
          </li>
          <li>
            <span className={`${layout.mark} ${styles.markAforo}`} aria-hidden="true" />
            {t(lang, "aforo")}
          </li>
          <li>
            <span className={`${layout.mark} ${styles.markModel}`} aria-hidden="true" />
            {t(lang, "oliveye")}
          </li>
          <li>
            <span className={`${layout.mark} ${styles.markForecast}`} aria-hidden="true" />
            {t(lang, "forecast")} · {t(lang, "interval")}
          </li>
          <li>
            <span className={`${layout.mark} ${styles.markSelected}`} aria-hidden="true" />
            {t(lang, "selectedCampaign")} ({campaign})
          </li>
        </ul>

        <div className={layout.panels}>
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

        <p className={layout.note}>
          {t(lang, "derivedNote")} {lang === "es" ? "Fuente:" : "Source:"} Junta de Andalucía
          (aforos), AICA.
        </p>

        <button
          type="button"
          className={layout.tableToggle}
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
  const [theme] = useTheme();
  const c = chartColours(theme);

  return (
    <figure className={layout.panel}>
      <figcaption className={layout.panelTitle}>{province}</figcaption>
      <div className={layout.chart}>
        <ComposedChart
          responsive
          data={data}
          style={{ width: "100%", height: "100%" }}
          margin={{ top: 8, right: 12, bottom: 0, left: 4 }}
        >
          <CartesianGrid vertical={false} stroke={c.grid} />
          {inRange && (
            <ReferenceLine
              x={campaign}
              stroke={c.highlight}
              strokeOpacity={0.3}
              strokeWidth={22}
              ifOverflow="hidden"
            />
          )}
          <XAxis
            dataKey="campaign"
            tickLine={false}
            axisLine={{ stroke: c.axis }}
            tick={{ fontSize: 11, fill: c.tick }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={56}
            tick={{ fontSize: 11, fill: c.tick }}
            tickFormatter={(v: number) => formatTonnes(v, lang, true)}
            domain={[0, "auto"]}
          />
          <Tooltip
            contentStyle={c.tooltip}
            formatter={(value, name) => [
              typeof value === "number" ? formatTonnes(value, lang) : "—",
              String(name),
            ]}
          />
          <Line
            name={t(lang, "aforo")}
            dataKey="aforo"
            stroke={c.aforo}
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={{ r: 3, fill: c.aforo, strokeWidth: 0 }}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            name={t(lang, "oliveye")}
            dataKey="oliveye"
            stroke={c.oliveye}
            strokeWidth={2.5}
            dot={{ r: 3, fill: c.oliveye, strokeWidth: 0 }}
            isAnimationActive={false}
          />
          <Line
            name={t(lang, "real")}
            dataKey="real"
            stroke={c.real}
            strokeWidth={1}
            dot={{ r: 4.5, fill: c.real, stroke: c.halo, strokeWidth: 1.5 }}
            isAnimationActive={false}
          />
          <Scatter
            name={t(lang, "forecast")}
            dataKey="forecast"
            fill={c.oliveye}
            shape="diamond"
            isAnimationActive={false}
          >
            <ErrorBar
              dataKey="bandError"
              width={10}
              stroke={c.oliveye}
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
    <div className={layout.tableWrap}>
      <table className={layout.table}>
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
