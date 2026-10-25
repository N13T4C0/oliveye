"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import { listRows, matchesSearch, sortRows, type Campaign, type SortMode } from "@/lib/campaigns";
import { ANOMALY_NO_DATA, anomalyOf, anomalyRamp, type Anomaly } from "@/lib/farm";
import { t } from "@/lib/i18n";
import type { Mode } from "@/lib/mode";
import {
  colourOf,
  formatIndex,
  formatSignedPercent,
  quantileBreaks,
  rampOf,
  type Lang,
} from "@/lib/scale";
import { PALETTES, useTheme } from "@/lib/theme";
import type { IndexKey, MunicipalityProperties } from "@/lib/types";

import { Legend } from "./Legend";
import { OliveMap } from "./OliveMap";
import { Segmented } from "./Segmented";
import { SeriesPanel } from "./SeriesPanel";
import styles from "./Workbench.module.css";

const CLASSES = 6;

interface Props {
  lang: Lang;
  campaign: Campaign;
  index: IndexKey;
  mode: Mode;
  features: MunicipalityProperties[];
  selected: MunicipalityProperties | null;
  onFeatures: (features: MunicipalityProperties[]) => void;
  onSelect: (id: string | null) => void;
}

export function Workbench({
  lang,
  campaign,
  index,
  mode,
  features,
  selected,
  onFeatures,
  onSelect,
}: Props) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("value");
  const [theme] = useTheme();
  const noData = PALETTES[theme].noData;

  // Breaks over every campaign: the same colour means the same value in every year.
  const breaks = useMemo(
    () =>
      quantileBreaks(
        features.flatMap((f) =>
          Object.values(f.indices)
            .map((i) => i[index])
            .filter((v): v is number => v !== null),
        ),
        CLASSES,
      ),
    [features, index],
  );

  const simple = mode === "simple";
  // Simple view: each municipality against its own other campaigns.
  const anomalies = useMemo(
    () =>
      new Map<string, Anomaly | null>(
        features.map((f) => [
          `${f.province_code}-${f.municipality_code}`,
          anomalyOf(f, index, campaign),
        ]),
      ),
    [features, index, campaign],
  );

  const rows = useMemo(() => {
    let all = listRows(features, index, campaign).filter((r) => matchesSearch(r.name, query));
    if (simple) {
      // Sorted by how unusual the campaign is (the z-score the colours come from): greenest
      // first for greenness, thirstiest first for thirst (a low NDMI means more thirst).
      const sign = index === "ndvi_spring" ? 1 : -1;
      all = all.map((r) => {
        const anomaly = anomalies.get(r.id);
        return { ...r, value: anomaly ? sign * anomaly.z : null };
      });
    }
    return sortRows(all, sort, lang);
  }, [features, index, campaign, query, sort, lang, simple, anomalies]);

  const swatch = (id: string, value: number | null): string => {
    if (!simple) return colourOf(value, breaks, ramp, noData);
    const anomaly = anomalies.get(id);
    return anomaly ? anomalyRamp(index, theme === "dark")[anomaly.cls] : ANOMALY_NO_DATA[theme];
  };
  const display = (id: string, value: number | null): string => {
    if (!simple) return formatIndex(value, lang);
    const anomaly = anomalies.get(id);
    if (!anomaly) return "—";
    return index === "ndvi_spring"
      ? formatSignedPercent(anomaly.pct, lang)
      : t(lang, `tShort${anomaly.cls}` as const);
  };

  const mapArea = useRef<HTMLDivElement>(null);
  // After a selection, scroll just enough for the series drawer (at the map's bottom) to show.
  const select = useCallback(
    (id: string | null) => {
      onSelect(id);
      const area = mapArea.current;
      if (id && area && area.getBoundingClientRect().bottom > window.innerHeight) {
        area.scrollIntoView({ behavior: "smooth", block: "end" });
      }
    },
    [onSelect],
  );

  const ramp = rampOf(index, theme === "dark");
  const selectedId = selected ? `${selected.province_code}-${selected.municipality_code}` : null;

  return (
    <section id="workbench" className={styles.workbench} aria-label={t(lang, "mapTitle")}>
      <aside className={styles.panel}>
        <div className={styles.panelHead}>
          <label className={styles.search}>
            <span className="visually-hidden">{t(lang, "search")}</span>
            <svg viewBox="0 0 20 20" aria-hidden="true" className={styles.searchIcon}>
              <circle
                cx="8.5"
                cy="8.5"
                r="5.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              />
              <path
                d="M12.6 12.6 17 17"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
            <input
              type="search"
              value={query}
              placeholder={t(lang, "search")}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <div className={styles.listMeta}>
            <span className="num">{t(lang, "municipalities", { n: rows.length })}</span>
            <Segmented
              label={lang === "es" ? "Orden" : "Order"}
              value={sort}
              onChange={setSort}
              options={[
                {
                  value: "value",
                  label: simple
                    ? t(lang, index === "ndvi_spring" ? "greenness" : "thirst")
                    : index === "ndvi_spring"
                      ? "NDVI"
                      : "NDMI",
                },
                { value: "name", label: "A–Z" },
              ]}
            />
          </div>
        </div>
        <ul className={styles.list}>
          {features.length === 0 ? (
            <li className={styles.empty}>{t(lang, "loadingMap")}</li>
          ) : rows.length === 0 ? (
            <li className={styles.empty}>{t(lang, "searchEmpty")}</li>
          ) : (
            rows.map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  className={styles.row}
                  aria-pressed={row.id === selectedId}
                  onClick={() => select(row.id === selectedId ? null : row.id)}
                >
                  <span
                    className={styles.swatch}
                    style={{ background: swatch(row.id, row.value) }}
                    aria-hidden="true"
                  />
                  <span className={styles.name}>
                    {row.name}
                    <span className={styles.province}>
                      {row.provinceCode === "23" ? "Jaén" : "Granada"}
                    </span>
                  </span>
                  <span className={`${styles.value} num`}>{display(row.id, row.value)}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      </aside>

      <div ref={mapArea} className={styles.mapArea}>
        <OliveMap
          lang={lang}
          campaign={campaign}
          index={index}
          mode={mode}
          breaks={breaks}
          selectedId={selectedId}
          onFeatures={onFeatures}
          onSelect={select}
        />
        <Legend
          lang={lang}
          campaign={campaign}
          index={index}
          mode={mode}
          breaks={breaks}
          compact={selected !== null}
        />
        <SeriesPanel
          lang={lang}
          campaign={campaign}
          index={index}
          mode={mode}
          municipality={selected}
          onClose={() => onSelect(null)}
        />
      </div>
    </section>
  );
}
