"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import { listRows, matchesSearch, sortRows, type Campaign, type SortMode } from "@/lib/campaigns";
import { t } from "@/lib/i18n";
import { colourOf, formatIndex, quantileBreaks, RAMPS, type Lang } from "@/lib/scale";
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
  features: MunicipalityProperties[];
  selected: MunicipalityProperties | null;
  onFeatures: (features: MunicipalityProperties[]) => void;
  onSelect: (id: string | null) => void;
}

export function Workbench({
  lang,
  campaign,
  index,
  features,
  selected,
  onFeatures,
  onSelect,
}: Props) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("value");

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

  const rows = useMemo(() => {
    const all = listRows(features, index, campaign).filter((r) => matchesSearch(r.name, query));
    return sortRows(all, sort, lang);
  }, [features, index, campaign, query, sort, lang]);

  const mapArea = useRef<HTMLDivElement>(null);
  // On narrow screens the map sits below the list: scroll so the series drawer is visible.
  const select = useCallback(
    (id: string | null) => {
      onSelect(id);
      if (id && window.matchMedia("(max-width: 860px)").matches) {
        mapArea.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      }
    },
    [onSelect],
  );

  const ramp = RAMPS[index];
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
                { value: "value", label: index === "ndvi_spring" ? "NDVI" : "NDMI" },
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
                    style={{ background: colourOf(row.value, breaks, ramp) }}
                    aria-hidden="true"
                  />
                  <span className={styles.name}>
                    {row.name}
                    <span className={styles.province}>
                      {row.provinceCode === "23" ? "Jaén" : "Granada"}
                    </span>
                  </span>
                  <span className={`${styles.value} num`}>{formatIndex(row.value, lang)}</span>
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
          breaks={breaks}
          selectedId={selectedId}
          onFeatures={onFeatures}
          onSelect={select}
        />
        <Legend lang={lang} campaign={campaign} index={index} breaks={breaks} />
        <SeriesPanel
          lang={lang}
          campaign={campaign}
          index={index}
          municipality={selected}
          onClose={() => onSelect(null)}
        />
      </div>
    </section>
  );
}
