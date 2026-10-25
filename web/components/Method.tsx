import { t } from "@/lib/i18n";
import type { Mode } from "@/lib/mode";
import type { Lang } from "@/lib/scale";
import { API_URL } from "@/lib/api";

import styles from "./Method.module.css";

const REPO = "https://github.com/N13T4C0/oliveye";

interface Props {
  lang: Lang;
  mode: Mode;
  onShowTechnical: () => void;
}

/** How it was validated (two sentences, DESIGN.md callout) plus sources and links. */
export function Method({ lang, mode, onShowTechnical }: Props) {
  const simple = mode === "simple";
  return (
    <>
      <section className={styles.section} aria-labelledby="method-title">
        <div className={styles.callout}>
          <h2 id="method-title" className={styles.title}>
            {t(lang, simple ? "methodTitleSimple" : "methodTitle")}
          </h2>
          <p>{t(lang, simple ? "method1Simple" : "method1")}</p>
          <p>{t(lang, simple ? "method2Simple" : "method2")}</p>
          {simple ? (
            <button type="button" className={styles.linkButton} onClick={onShowTechnical}>
              {t(lang, "showTechnical")}
            </button>
          ) : (
            <a href={`${REPO}/blob/main/docs/results/README.md`}>{t(lang, "methodLink")}</a>
          )}
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
