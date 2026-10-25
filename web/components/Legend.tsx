"use client";

import { ANOMALY_RAMPS } from "@/lib/farm";
import { t } from "@/lib/i18n";
import type { Mode } from "@/lib/mode";
import { formatIndex, rampOf, type Lang } from "@/lib/scale";
import { PALETTES, useTheme } from "@/lib/theme";
import type { IndexKey } from "@/lib/types";

import styles from "./Legend.module.css";

interface Props {
  lang: Lang;
  campaign: string;
  index: IndexKey;
  mode: Mode;
  breaks: number[];
  /** Hide the explanations while the series panel is open, so the two never overlap. */
  compact?: boolean;
}

/** Floating map legend: what the colour means, with the exact palette and class limits. */
export function Legend({ lang, campaign, index, mode, breaks, compact = false }: Props) {
  const [theme] = useTheme();
  if (mode === "simple") {
    return <SimpleLegend lang={lang} campaign={campaign} index={index} compact={compact} />;
  }
  const ramp = rampOf(index, theme === "dark");
  const isNdvi = index === "ndvi_spring";
  return (
    <div className={styles.legend}>
      <p className={styles.title}>
        {t(lang, isNdvi ? "ndviName" : "ndmiName")} <span className="num">{campaign}</span>
      </p>
      {!compact && <p className={styles.help}>{t(lang, isNdvi ? "ndviHelp" : "ndmiHelp")}</p>}
      {breaks.length > 0 && (
        <div
          className={styles.scale}
          role="img"
          aria-label={`${t(lang, isNdvi ? "ndviName" : "ndmiName")}: ${breaks.map((b) => formatIndex(b, lang)).join(", ")}`}
        >
          <div className={styles.swatches}>
            {ramp.map((colour) => (
              <span key={colour} style={{ background: colour }} />
            ))}
          </div>
          <div className={`${styles.ticks} num`} aria-hidden="true">
            {breaks.map((b) => (
              <span key={b}>{formatIndex(b, lang)}</span>
            ))}
          </div>
          <p className={styles.ends} aria-hidden="true">
            <span>
              {isNdvi
                ? lang === "es"
                  ? "menos verde"
                  : "less green"
                : lang === "es"
                  ? "más seco"
                  : "drier"}
            </span>
            <span>
              {isNdvi
                ? lang === "es"
                  ? "más verde"
                  : "greener"
                : lang === "es"
                  ? "más agua"
                  : "more water"}
            </span>
          </p>
        </div>
      )}
      <p className={styles.noData}>
        <span style={{ background: PALETTES[theme].noData }} aria-hidden="true" />{" "}
        {t(lang, "noData")}
      </p>
      {!compact && <p className={styles.note}>{t(lang, "mapNote")}</p>}
    </div>
  );
}

/** Simple view: five plain-language classes, from "much less than usual" to "much more". */
function SimpleLegend({
  lang,
  campaign,
  index,
  compact,
}: {
  lang: Lang;
  campaign: string;
  index: IndexKey;
  compact: boolean;
}) {
  const [theme] = useTheme();
  const isNdvi = index === "ndvi_spring";
  const prefix = isNdvi ? "g" : "t";
  // Listed from "more of it" to "less": greener first, thirstier first.
  const classes = isNdvi ? ([4, 3, 2, 1, 0] as const) : ([0, 1, 2, 3, 4] as const);
  return (
    <div className={styles.legend}>
      <p className={styles.title}>
        {t(lang, isNdvi ? "greennessName" : "thirstName")} <span className="num">{campaign}</span>
      </p>
      {!compact && (
        <p className={styles.help}>{t(lang, isNdvi ? "greennessHelp" : "thirstHelp")}</p>
      )}
      <ul className={styles.classes}>
        {classes.map((cls) => (
          <li key={cls}>
            <span style={{ background: ANOMALY_RAMPS[index][cls] }} aria-hidden="true" />
            {t(lang, `${prefix}${cls}` as const)}
          </li>
        ))}
        <li>
          <span style={{ background: PALETTES[theme].noData }} aria-hidden="true" />
          {t(lang, "noData")}
        </li>
      </ul>
    </div>
  );
}
