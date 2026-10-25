"use client";

import { useEffect, useMemo, useState } from "react";

import { DEFAULT_CAMPAIGN, type Campaign } from "@/lib/campaigns";
import type { Lang } from "@/lib/scale";
import { useTheme } from "@/lib/theme";
import type { IndexKey, MunicipalityProperties, PageData } from "@/lib/types";

import { ErrorSection } from "./ErrorSection";
import { Method } from "./Method";
import { ProvinceSection } from "./ProvinceSection";
import { TopBar } from "./TopBar";
import { Verdict } from "./Verdict";
import { Workbench } from "./Workbench";

/**
 * Owns the state every part of the page shares: language, campaign, index and the selected
 * municipality. Choosing a campaign recolours the map and highlights it in the province chart.
 */
export function Dashboard({ data }: { data: PageData }) {
  const [lang, setLang] = useState<Lang>("es");
  const [campaign, setCampaign] = useState<Campaign>(DEFAULT_CAMPAIGN);
  const [index, setIndex] = useState<IndexKey>("ndvi_spring");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [features, setFeatures] = useState<MunicipalityProperties[]>([]);
  const [theme, setTheme] = useTheme();

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const selected = useMemo(
    () => features.find((f) => `${f.province_code}-${f.municipality_code}` === selectedId) ?? null,
    [features, selectedId],
  );

  return (
    <>
      <a className="skip-link" href="#workbench">
        {lang === "es" ? "Saltar al mapa" : "Skip to the map"}
      </a>
      <TopBar
        lang={lang}
        campaign={campaign}
        index={index}
        theme={theme}
        onLang={setLang}
        onTheme={setTheme}
        onCampaign={setCampaign}
        onIndex={setIndex}
      />
      <main>
        <Verdict lang={lang} summary={data.summary} forecast={data.forecast} />
        <Workbench
          lang={lang}
          campaign={campaign}
          index={index}
          features={features}
          selected={selected}
          onFeatures={setFeatures}
          onSelect={setSelectedId}
        />
        <ProvinceSection
          lang={lang}
          campaign={campaign}
          production={data.production}
          forecast={data.forecast}
        />
        <ErrorSection
          lang={lang}
          campaign={campaign}
          production={data.production}
          scores={data.summary}
        />
        <Method lang={lang} />
      </main>
    </>
  );
}
