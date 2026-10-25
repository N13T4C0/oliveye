"use client";

import { INDEX_CAMPAIGNS, type Campaign } from "@/lib/campaigns";
import { t } from "@/lib/i18n";
import type { Lang } from "@/lib/scale";
import type { Theme } from "@/lib/theme";
import type { IndexKey } from "@/lib/types";

import { Segmented } from "./Segmented";
import styles from "./TopBar.module.css";

interface Props {
  lang: Lang;
  campaign: Campaign;
  index: IndexKey;
  theme: Theme;
  onLang: (lang: Lang) => void;
  onTheme: (theme: Theme) => void;
  onCampaign: (campaign: Campaign) => void;
  onIndex: (index: IndexKey) => void;
}

export function TopBar({
  lang,
  campaign,
  index,
  theme,
  onLang,
  onTheme,
  onCampaign,
  onIndex,
}: Props) {
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <header className={styles.bar}>
      <div className={styles.inner}>
        <a className={styles.brand} href="#" aria-label="OlivEye">
          <svg className={styles.mark} viewBox="0 0 24 24" aria-hidden="true">
            <ellipse
              cx="12"
              cy="12"
              rx="10.5"
              ry="6.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
            />
            <ellipse
              cx="12"
              cy="12"
              rx="3.2"
              ry="4.4"
              fill="var(--lime)"
              transform="rotate(-28 12 12)"
            />
          </svg>
          OlivEye
        </a>
        <div className={styles.controls}>
          <label className={styles.campaign}>
            <span className={styles.label}>{t(lang, "campaign")}</span>
            <select
              className={styles.select}
              value={campaign}
              onChange={(event) => onCampaign(event.target.value as Campaign)}
            >
              {INDEX_CAMPAIGNS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <Segmented
            label={t(lang, "index")}
            value={index}
            onChange={onIndex}
            tone="ink"
            options={[
              { value: "ndvi_spring", label: t(lang, "ndviShort") },
              { value: "ndmi_summer", label: t(lang, "ndmiShort") },
            ]}
          />
          <Segmented
            label={t(lang, "language")}
            value={lang}
            onChange={onLang}
            tone="ink"
            options={[
              { value: "es", label: "ES" },
              { value: "en", label: "EN" },
            ]}
          />
          <button
            type="button"
            className={styles.theme}
            aria-label={t(lang, next === "dark" ? "themeToDark" : "themeToLight")}
            title={t(lang, next === "dark" ? "themeToDark" : "themeToLight")}
            onClick={() => onTheme(next)}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </div>
    </header>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path
        d="M16.2 12.6A6.6 6.6 0 0 1 7.4 3.8a6.6 6.6 0 1 0 8.8 8.8Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="3.6" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M10 1.8v2.1M10 16.1v2.1M1.8 10h2.1M16.1 10h2.1M4.2 4.2l1.5 1.5M14.3 14.3l1.5 1.5M4.2 15.8l1.5-1.5M14.3 5.7l1.5-1.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}
