import {
  formatEuroRange,
  formatKgPerHa,
  harvestValue,
  kgPerHectare,
  tonnesToLitres,
} from "@/lib/farm";
import { t } from "@/lib/i18n";
import type { Lang } from "@/lib/scale";
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

/**
 * The simple view's opening band: the official forecast in litres, kilos per hectare and euros,
 * with the satellite estimate beside it, clearly labelled as experimental.
 */
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
  const ratio = ridge && aforo ? Math.round(ridge / aforo) : null;
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
                    {lang === "es" ? "Provincia" : "Province"}
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
                              {formatKgPerHa(
                                kgPerHectare(tonnes, hectares(PROVINCE_CODES[row.province])),
                                lang,
                              ).replace(" kg/ha", "")}
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {ratio !== null && (
              <p className={styles.tileNote}>{t(lang, "harvestSatelliteNote", { ratio })}</p>
            )}
          </figure>
        </div>
        <p className={styles.caption}>
          {price
            ? t(lang, "harvestCaption", {
                start: date(price.week_start),
                end: date(price.week_end),
                low: decimal(price.low_eur_per_kg),
                high: decimal(price.high_eur_per_kg),
              })
            : t(lang, "harvestCaptionNoPrice")}{" "}
          {price && (
            <a href={price.source_url} className={styles.captionLink}>
              {lang === "es" ? "Fuente del precio" : "Price source"}
            </a>
          )}
        </p>
      </div>
    </section>
  );
}
