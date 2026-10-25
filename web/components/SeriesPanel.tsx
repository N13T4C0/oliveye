"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceArea, Tooltip, XAxis, YAxis } from "recharts";

import { getMunicipalitySeries } from "@/lib/api";
import { anomalyOf, SMALL_SAMPLE_CELLS } from "@/lib/farm";
import { t } from "@/lib/i18n";
import type { Mode } from "@/lib/mode";
import { campaignWindow, formatIndex, type Lang } from "@/lib/scale";
import { chartColours, useTheme } from "@/lib/theme";
import type { IndexKey, MonthlyIndex, MunicipalityProperties } from "@/lib/types";

import styles from "./SeriesPanel.module.css";

interface Props {
  lang: Lang;
  campaign: string;
  index: IndexKey;
  mode: Mode;
  municipality: MunicipalityProperties | null;
  onClose: () => void;
}

type Result = MonthlyIndex[] | "error";

/** Bottom drawer over the map: ten years of monthly NDVI or NDMI for one municipality. */
export function SeriesPanel({ lang, campaign, index, mode, municipality, onClose }: Props) {
  // Results per municipality: fetched once, then reused when the visitor comes back to it.
  const [results, setResults] = useState<Record<string, Result>>({});
  const [theme] = useTheme();
  const c = chartColours(theme);
  const id = municipality
    ? `${municipality.province_code}-${municipality.municipality_code}`
    : null;
  const result = id ? results[id] : undefined;

  useEffect(() => {
    if (!municipality || !id || result !== undefined) return;
    const controller = new AbortController();
    getMunicipalitySeries(
      municipality.province_code,
      municipality.municipality_code,
      controller.signal,
    )
      .then((series) => setResults((prev) => ({ ...prev, [id]: series })))
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError"))
          setResults((prev) => ({ ...prev, [id]: "error" }));
      });
    return () => controller.abort();
  }, [id, municipality, result]);

  const state =
    result === undefined
      ? { status: "loading" as const }
      : result === "error"
        ? { status: "error" as const }
        : { status: "ready" as const, series: result };

  if (!municipality) {
    return <p className={styles.hint}>{t(lang, "seriesHint")}</p>;
  }

  const key = index === "ndvi_spring" ? "ndvi" : "ndmi";
  const colour = index === "ndvi_spring" ? c.oliveye : c.aforo;
  const window = campaignWindow(campaign);
  const data =
    state.status === "ready" ? state.series.map((p) => ({ month: p.month, value: p[key] })) : [];
  const hasWindow = data.some((d) => d.month >= window.start && d.month <= window.end);
  const simple = mode === "simple";
  const sentence = simple ? plainSentence(municipality, index, campaign, lang) : null;

  return (
    <section
      className={styles.panel}
      aria-label={t(lang, "seriesTitle", { name: municipality.name })}
    >
      <header className={styles.head}>
        <div>
          <h2 className={styles.title}>{municipality.name}</h2>
          <p className={styles.sub}>
            {simple
              ? t(lang, index === "ndvi_spring" ? "monthlyGreenness" : "monthlyThirst")
              : `${index === "ndvi_spring" ? "NDVI" : "NDMI"} · ${lang === "es" ? "mediana mensual" : "monthly median"}`}{" "}
            ·{" "}
            <span className="num">
              {new Intl.NumberFormat(lang === "es" ? "es-ES" : "en-GB").format(
                Math.round(municipality.olive_ha),
              )}
            </span>{" "}
            {t(lang, "hectares")}
          </p>
        </div>
        <button
          type="button"
          className={styles.close}
          onClick={onClose}
          aria-label={t(lang, "close")}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path
              d="M3.5 3.5l9 9M12.5 3.5l-9 9"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </header>

      {sentence && <p className={styles.sentence}>{sentence}</p>}
      {simple && municipality.cells < SMALL_SAMPLE_CELLS && (
        <p className={styles.caveat}>
          {t(lang, "smallSample", { ha: Math.round(municipality.olive_ha) })}
        </p>
      )}
      {state.status === "loading" && <p className={styles.status}>{t(lang, "seriesLoading")}</p>}
      {state.status === "error" && (
        <p className={styles.status} role="alert">
          {t(lang, "seriesError")}
        </p>
      )}
      {state.status === "ready" && (
        <div className={styles.chart}>
          <LineChart
            responsive
            data={data}
            style={{ width: "100%", height: "100%" }}
            margin={{ top: 8, right: 8, bottom: 0, left: -12 }}
          >
            <CartesianGrid vertical={false} stroke={c.grid} />
            {hasWindow && (
              <ReferenceArea
                x1={window.start}
                x2={window.end}
                fill={c.highlight}
                fillOpacity={0.3}
                stroke="none"
                ifOverflow="hidden"
              />
            )}
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={{ stroke: c.axis }}
              tick={{ fontSize: 11, fill: c.tick }}
              ticks={data.filter((d) => d.month.endsWith("-01")).map((d) => d.month)}
              tickFormatter={(m: string) => m.slice(0, 4)}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={simple ? 8 : 44}
              tick={simple ? false : { fontSize: 11, fill: c.tick }}
              tickFormatter={(v: number) => formatIndex(v, lang)}
              domain={["auto", "auto"]}
            />
            <Tooltip
              cursor={{ stroke: c.cursor, strokeDasharray: "3 3" }}
              contentStyle={c.tooltip}
              labelFormatter={(label) => String(label)}
              formatter={(value) => [
                formatIndex(typeof value === "number" ? value : null, lang),
                key.toUpperCase(),
              ]}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={colour}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </div>
      )}
      {state.status === "ready" && hasWindow && (
        <p className={styles.window}>
          <span aria-hidden="true" /> {t(lang, "seriesWindow", { campaign })}
        </p>
      )}
    </section>
  );
}

/** "En la primavera de la campaña 2026/27, el olivar de Martos ha estado un 8 % menos verde…" */
function plainSentence(
  municipality: MunicipalityProperties,
  index: IndexKey,
  campaign: string,
  lang: Lang,
): string | null {
  const anomaly = anomalyOf(municipality, index, campaign);
  if (!anomaly) return null;
  const name = municipality.name;
  if (index === "ndvi_spring") {
    const pct = `${new Intl.NumberFormat(lang === "es" ? "es-ES" : "en-GB", {
      maximumFractionDigits: 0,
    }).format(Math.abs(anomaly.pct))}\u00a0%`;
    return t(lang, "greennessSentence", {
      campaign,
      name,
      pct,
      dir: t(lang, anomaly.pct >= 0 ? "more" : "less"),
    });
  }
  const label =
    anomaly.cls === 2 ? t(lang, "thirstUsual") : t(lang, `t${anomaly.cls}` as const).toLowerCase();
  return t(lang, "thirstSentence", { campaign, name, label });
}
