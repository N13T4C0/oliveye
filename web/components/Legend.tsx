import { t } from "@/lib/i18n";
import { formatIndex, NO_DATA, RAMPS, type Lang } from "@/lib/scale";
import type { IndexKey } from "@/lib/types";

import styles from "./Legend.module.css";

interface Props {
  lang: Lang;
  campaign: string;
  index: IndexKey;
  breaks: number[];
  /** Hide the explanations while the series panel is open, so the two never overlap. */
  compact?: boolean;
}

/** Floating map legend: what the colour means, with the exact palette and class limits. */
export function Legend({ lang, campaign, index, breaks, compact = false }: Props) {
  const ramp = RAMPS[index];
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
        <span style={{ background: NO_DATA }} aria-hidden="true" /> {t(lang, "noData")}
      </p>
      {!compact && <p className={styles.note}>{t(lang, "mapNote")}</p>}
    </div>
  );
}
