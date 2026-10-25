import { t } from "@/lib/i18n";
import type { Lang } from "@/lib/scale";
import { API_URL } from "@/lib/api";

import styles from "./Method.module.css";

const REPO = "https://github.com/N13T4C0/oliveye";

/** How it was validated (two sentences, DESIGN.md callout) plus sources and links. */
export function Method({ lang }: { lang: Lang }) {
  return (
    <>
      <section className={styles.section} aria-labelledby="method-title">
        <div className={styles.callout}>
          <h2 id="method-title" className={styles.title}>
            {t(lang, "methodTitle")}
          </h2>
          <p>{t(lang, "method1")}</p>
          <p>{t(lang, "method2")}</p>
          <a href={`${REPO}/blob/main/docs/results/README.md`}>{t(lang, "methodLink")}</a>
        </div>
      </section>
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div>
            <h2 className={styles.footerTitle}>{t(lang, "sourcesTitle")}</h2>
            <p>{t(lang, "sources")}</p>
          </div>
          <div className={styles.links}>
            <a href={REPO}>{t(lang, "codeLink")}</a>
            <a href={`${API_URL}/docs`}>{t(lang, "apiLink")}</a>
          </div>
          <p className={styles.small}>{t(lang, "footerNote")}</p>
        </div>
      </footer>
    </>
  );
}
