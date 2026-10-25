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
import { formatMillionLitres, tonnesToLitres } from "@/lib/farm";
import type { Mode } from "@/lib/mode";
import { formatTonnes, type Lang } from "@/lib/scale";
import { chartColours, useTheme } from "@/lib/theme";
import type { Forecast, ProductionPoint, ProvinceName } from "@/lib/types";

import layout from "./ChartSection.module.css";
import styles from "./ProvinceSection.module.css";

const PROVINCES: ProvinceName[] = ["Jaén", "Granada"];

/** How quantities are shown: tonnes (technical view) or million litres (simple view). */
interface Units {
  technical: boolean;
  convert: (tonnes: number) => number;
  /** Axis ticks and table cells: "392 kt" or "628". */
  short: (value: number | null) => string;
  /** Tooltips: "392.300 t" or "628 millones de litros". */
  full: (value: number | null) => string;
  /** Table header suffix. */
  header: string;
}

function unitsFor(mode: Mode, lang: Lang, density: number | undefined): Units {
  if (mode === "technical") {
    return {
      technical: true,
      convert: (tonnes) => tonnes,
      short: (v) => formatTonnes(v, lang, true),
      full: (v) => formatTonnes(v, lang),
      header: "(t)",
    };
  }
  const millions = new Intl.NumberFormat(lang === "es" ? "es-ES" : "en-GB", {
    maximumFractionDigits: 0,
  });
  return {
    technical: false,
    convert: (tonnes) => tonnesToLitres(tonnes, density),
    short: (v) => (v === null ? "—" : millions.format(v / 1e6)),
    full: (v) => formatMillionLitres(v, lang),
    header: lang === "es" ? "(millones de litros)" : "(million litres)",
  };
}

function convertRow(row: ProvinceChartRow, convert: (t: number) => number): ProvinceChartRow {
  const c = (v: number | null) => (v === null ? null : convert(v));
  return {
    ...row,
    real: c(row.real),
    aforo: c(row.aforo),
    oliveye: c(row.oliveye),
    forecast: c(row.forecast),
    band: row.band ? [convert(row.band[0]), convert(row.band[1])] : null,
  };
}

interface Props {
  lang: Lang;
  campaign: string;
  production: Record<ProvinceName, ProductionPoint[]>;
  forecast: Forecast;
  mode: Mode;
  /** Oil density (kg/L) published with the reference price; a standard value otherwise. */
  density?: number;
}

/** Real production, aforo and OlivEye per campaign, one panel per province (own y-axis). */
export function ProvinceSection({ lang, campaign, production, forecast, mode, density }: Props) {
  const units = unitsFor(mode, lang, density);
  const simple = mode === "simple";
  const [showTable, setShowTable] = useState(false);

  return (
    <section className={layout.section} aria-labelledby="provinces-title">
      <div className={layout.inner}>
        <header className={layout.head}>
          <h2 id="provinces-title" className={layout.title}>
            {t(lang, simple ? "provincesTitleSimple" : "provincesTitle")}
          </h2>
          <p className={layout.lead}>{t(lang, simple ? "provincesLeadSimple" : "provincesLead")}</p>
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
            {t(lang, simple ? "satelliteShort" : "oliveye")}
          </li>
          <li>
            <span className={`${layout.mark} ${styles.markForecast}`} aria-hidden="true" />
            {simple
              ? t(lang, "satelliteForecast")
              : `${t(lang, "forecast")} · ${t(lang, "interval")}`}
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
            ).map((r) => convertRow(r, units.convert));
            return (
              <ProvincePanel
                key={province}
                lang={lang}
                province={province}
                campaign={campaign}
                rows={rows}
                units={units}
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
        {showTable && (
          <ProductionTable lang={lang} production={production} forecast={forecast} units={units} />
        )}
      </div>
    </section>
  );
}

function ProvincePanel({
  lang,
  province,
  campaign,
  rows,
  units,
}: {
  lang: Lang;
  province: ProvinceName;
  campaign: string;
  rows: ProvinceChartRow[];
  units: Units;
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
            tickFormatter={(v: number) => units.short(v)}
            domain={[0, "auto"]}
          />
          <Tooltip
            contentStyle={c.tooltip}
            formatter={(value, name) => [
              typeof value === "number" ? units.full(value) : "—",
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
            name={t(lang, units.technical ? "oliveye" : "satelliteShort")}
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
  units,
}: {
  lang: Lang;
  production: Record<ProvinceName, ProductionPoint[]>;
  forecast: Forecast;
  units: Units;
}) {
  // Full precision in the technical view (tonnes); short millions of litres in the simple one.
  const cell = (tonnes: number | null) =>
    tonnes === null
      ? "—"
      : units.technical
        ? units.full(tonnes)
        : units.short(units.convert(tonnes));
  const range = (tonnes: number) => units.short(units.convert(tonnes));
  return (
    <div className={layout.tableWrap}>
      <table className={layout.table}>
        <caption className="visually-hidden">{t(lang, "provincesTitle")}</caption>
        <thead>
          <tr>
            <th scope="col">{lang === "es" ? "Provincia" : "Province"}</th>
            <th scope="col">{t(lang, "campaign")}</th>
            <th scope="col">
              {t(lang, "real")} {units.header}
            </th>
            <th scope="col">
              {t(lang, "aforo")} {units.header}
            </th>
            <th scope="col">
              {t(lang, units.technical ? "oliveye" : "satelliteShort")} {units.header}
            </th>
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
                  <td className="num">{cell(p.oil_final_t)}</td>
                  <td className="num">{cell(p.oil_aforo_t)}</td>
                  <td className="num">
                    {f
                      ? `${cell(f.pred_t)} (${range(f.low_t)}–${range(f.high_t)})`
                      : cell(p.pred_t)}
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
