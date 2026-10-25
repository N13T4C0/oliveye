"use client";

import { INDEX_CAMPAIGNS, type Campaign } from "@/lib/campaigns";
import { t } from "@/lib/i18n";
import type { Lang } from "@/lib/scale";
import type { IndexKey } from "@/lib/types";

import { Segmented } from "./Segmented";
import styles from "./TopBar.module.css";

interface Props {
  lang: Lang;
  campaign: Campaign;
  index: IndexKey;
  onLang: (lang: Lang) => void;
  onCampaign: (campaign: Campaign) => void;
  onIndex: (index: IndexKey) => void;
}

export function TopBar({ lang, campaign, index, onLang, onCampaign, onIndex }: Props) {
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
        </div>
      </div>
    </header>
  );
}
