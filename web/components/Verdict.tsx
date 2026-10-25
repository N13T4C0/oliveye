import { t } from "@/lib/i18n";
import { formatPercent, formatTonnes, type Lang } from "@/lib/scale";
import type { Forecast, ModelScore } from "@/lib/types";

import styles from "./Verdict.module.css";

interface Props {
  lang: Lang;
  summary: ModelScore[];
  forecast: Forecast;
}

/** The honest answer first: the question, "not yet", and the numbers that say why. */
export function Verdict({ lang, summary, forecast }: Props) {
  const ridge = summary.find((s) => s.model === "ridge");
  const aforo = summary.find((s) => s.model === "aforo");
  const baseline = summary.find((s) => s.model === "province_mean");
  const modelError = ridge?.mape_pct ?? null;
  const aforoError = aforo?.mape_pct ?? null;
  const baselineError = baseline?.mape_pct ?? null;
  const scale = Math.max(modelError ?? 0, aforoError ?? 0, baselineError ?? 0) || 1;
  const bars = [
    {
      key: "model",
      label: t(lang, "oliveye"),
      value: modelError,
      fill: styles.fillModel,
      text: "",
    },
    {
      key: "baseline",
      label: t(lang, "provinceMean"),
      value: baselineError,
      fill: styles.fillBaseline,
      text: styles.baseline,
    },
    {
      key: "aforo",
      label: t(lang, "aforo"),
      value: aforoError,
      fill: styles.fillAforo,
      text: styles.official,
    },
  ];
  const rows = [...forecast.rows].sort((a, b) =>
    a.province === "Jaén" ? -1 : b.province === "Jaén" ? 1 : 0,
  );

  return (
    <section className={styles.band} aria-labelledby="verdict-question">
      <div className={styles.inner}>
        <div className={styles.answer}>
          <h1 id="verdict-question" className={styles.question}>
            {t(lang, "question")} <span className={styles.no}>{t(lang, "answer")}</span>
          </h1>
          <p className={styles.detail}>{t(lang, "answerDetail")}</p>
        </div>

        <div className={styles.compare}>
          <figure className={styles.tile}>
            <figcaption className={styles.tileTitle}>
              {t(lang, "forecastTitle")} {forecast.campaign}
              <span className={styles.vs}> · {t(lang, "aforoTitle").toLowerCase()}</span>
            </figcaption>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col" className="visually-hidden">
                    {lang === "es" ? "Provincia" : "Province"}
                  </th>
                  <th scope="col">{t(lang, "oliveye")}</th>
                  <th scope="col">{t(lang, "aforo")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.province}>
                    <th scope="row">{row.province}</th>
                    <td>
                      <span className={`${styles.value} num`}>
                        {formatTonnes(row.pred_t, lang, true)}
                      </span>
                      <span className={`${styles.range} num`}>
                        {formatTonnes(row.low_t, lang, true)}–{formatTonnes(row.high_t, lang, true)}
                      </span>
                    </td>
                    <td>
                      <span className={`${styles.value} ${styles.official} num`}>
                        {formatTonnes(row.oil_aforo_t, lang, true)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className={styles.note}>
              {t(lang, "forecastNote")} · {t(lang, "aforoNote")}
            </p>
          </figure>

          <figure className={styles.tile}>
            <figcaption className={styles.tileTitle}>{t(lang, "mapeTitle")}</figcaption>
            <dl className={styles.bars}>
              {bars.map((bar) => (
                <div key={bar.key} className={styles.barRow}>
                  <dt>{bar.label}</dt>
                  <dd>
                    <span className={styles.track}>
                      <span
                        className={`${styles.fill} ${bar.fill}`}
                        style={{ inlineSize: `${((bar.value ?? 0) / scale) * 100}%` }}
                      />
                    </span>
                    <span className={`${styles.value} ${styles.small} ${bar.text} num`}>
                      {formatPercent(bar.value, lang)}
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
            <p className={styles.note}>
              {ridge
                ? t(lang, "aforoCloser", {
                    n: ridge.campaigns - ridge.campaign_wins_vs_aforo,
                    total: ridge.campaigns,
                  })
                : null}
              {" · "}
              {t(lang, "errorNote")}
            </p>
          </figure>
        </div>
      </div>
    </section>
  );
}
