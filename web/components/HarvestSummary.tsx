import {
  formatEuroRange,
  formatKgNumber,
  formatMillionLitres,
  harvestValue,
  kgPerHectare,
  tonnesToLitres,
} from "@/lib/farm";
import { t } from "@/lib/i18n";
import { formatPercent, type Lang } from "@/lib/scale";
import type { Forecast, ModelScore, Municipality, ReferencePrice } from "@/lib/types";

import styles from "./Verdict.module.css";

const PROVINCE_CODES = { Jaén: "23", Granada: "18" } as const;

interface Props {
  lang: Lang;
  forecast: Forecast;
  summary: ModelScore[];
  municipalities: Municipality[];
  price: ReferencePrice | null;
}

/** "628" in large type and "millones de litros" small beneath it, so the figure reads first. */
function Litres({ tonnes, density, lang }: { tonnes: number; density?: number; lang: Lang }) {
  const millions = tonnesToLitres(tonnes, density) / 1e6;
  const value = new Intl.NumberFormat(lang === "es" ? "es-ES" : "en-GB", {
    maximumFractionDigits: millions < 100 ? 1 : 0,
  }).format(millions);
  return (
    <>
      {value}
      <span className={styles.unit}>{t(lang, "millionLitres")}</span>
    </>
  );
}

/**
 * The simple view's opening band: the official forecast in litres, kilos per hectare and euros,
 * with the satellite estimate beside it, clearly labelled as experimental, with its margin.
 */
export function HarvestSummary({ lang, forecast, summary, municipalities, price }: Props) {
  const density = price?.oil_density_kg_per_l;
  const hectares = (code: string) =>
    municipalities
      .filter((m) => m.province_code === code)
      .reduce((sum, m) => sum + m.olive_hectares, 0);
  const rows = [...forecast.rows].sort((a, b) =>
    a.province === "Jaén" ? -1 : b.province === "Jaén" ? 1 : 0,
  );
  const ridge = summary.find((s) => s.model === "ridge")?.mape_pct;
  const aforo = summary.find((s) => s.model === "aforo")?.mape_pct;
  const last = summary.find((s) => s.model === "last_campaign")?.mape_pct;
  const millions = (tonnes: number) =>
    new Intl.NumberFormat(lang === "es" ? "es-ES" : "en-GB", { maximumFractionDigits: 0 }).format(
      tonnesToLitres(tonnes, density) / 1e6,
    );
  const decimal = (v: number) =>
    new Intl.NumberFormat(lang === "es" ? "es-ES" : "en-GB", {
      minimumFractionDigits: 2,
    }).format(v);
  const date = (iso: string) =>
    new Intl.DateTimeFormat(lang === "es" ? "es-ES" : "en-GB", {
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(new Date(`${iso}T12:00:00`));

  return (
    <section className={styles.band} aria-labelledby="harvest-title">
      <div className={styles.inner}>
        <div className={styles.answer}>
          <h1 id="harvest-title" className={styles.question}>
            {t(lang, "harvestTitle", { campaign: forecast.campaign })}
          </h1>
          <p className={styles.detail}>{t(lang, "harvestDetail")}</p>
        </div>

        <div className={styles.compare}>
          <figure className={styles.tile}>
            <figcaption className={styles.tileTitle}>{t(lang, "harvestAforo")}</figcaption>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col" className="visually-hidden">
                    {t(lang, "province")}
                  </th>
                  <th scope="col">{t(lang, "litresColumn")}</th>
                  <th scope="col">{t(lang, "kgPerHaColumn")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const tonnes = row.oil_aforo_t;
                  return (
                    <tr key={row.province}>
                      <th scope="row">{row.province}</th>
                      <td>
                        <span className={`${styles.value} ${styles.official} num`}>
                          {tonnes === null ? (
                            "—"
                          ) : (
                            <Litres tonnes={tonnes} density={density} lang={lang} />
                          )}
                        </span>
                        {tonnes !== null && price && (
                          <span className={`${styles.range} num`}>
                            {t(lang, "harvestValue")}:{" "}
                            {formatEuroRange(harvestValue(tonnes, price), lang)}
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={`${styles.value} ${styles.small} ${styles.neutral} num`}>
                          {tonnes === null ? (
                            "—"
                          ) : (
                            <>
                              {formatKgNumber(
                                kgPerHectare(tonnes, hectares(PROVINCE_CODES[row.province])),
                                lang,
                              )}
                              <span className={styles.unit}>kg/ha</span>
                            </>
                          )}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </figure>

          <figure className={styles.tile}>
            <figcaption className={styles.tileTitle}>{t(lang, "harvestSatellite")}</figcaption>
            <table className={styles.table}>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.province}>
                    <th scope="row">{row.province}</th>
                    <td>
                      <span className={`${styles.value} ${styles.small} num`}>
                        <Litres tonnes={row.pred_t} density={density} lang={lang} />
                      </span>
                      <span className={`${styles.range} num`}>
                        {t(lang, "satelliteRange", {
                          low: millions(row.low_t),
                          high: formatMillionLitres(tonnesToLitres(row.high_t, density), lang),
                        })}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {ridge !== undefined && aforo !== undefined && (
              <p className={styles.tileNote}>
                {t(lang, "harvestSatelliteNote", {
                  model: formatPercent(ridge, lang),
                  aforo: formatPercent(aforo, lang),
                  last: formatPercent(last ?? null, lang),
                })}
              </p>
            )}
          </figure>
        </div>
        <p className={styles.caption}>
          {price
            ? t(lang, "harvestCaption", {
                start: date(price.week_start),
                end: date(price.week_end),
                extra: decimal(price.eur_per_kg.virgen_extra),
                virgin: decimal(price.eur_per_kg.virgen),
                lampante: decimal(price.eur_per_kg.lampante),
              })
            : t(lang, "harvestCaptionNoPrice")}{" "}
          {price && (
            <a href={price.source_url} className={styles.captionLink}>
              {t(lang, "priceSource")}
            </a>
          )}
        </p>
      </div>
    </section>
  );
}
