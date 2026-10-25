"use client";

import { useEffect, useMemo, useState } from "react";

import { DEFAULT_CAMPAIGN, type Campaign } from "@/lib/campaigns";
import { useMode } from "@/lib/mode";
import type { Lang } from "@/lib/scale";
import { useTheme } from "@/lib/theme";
import type { IndexKey, MunicipalityProperties, PageData } from "@/lib/types";

import { ErrorSection } from "./ErrorSection";
import { HarvestSummary } from "./HarvestSummary";
import { Method } from "./Method";
import { ProvinceSection } from "./ProvinceSection";
import { TopBar } from "./TopBar";
import { Verdict } from "./Verdict";
import { Workbench } from "./Workbench";

/**
 * Owns the state every part of the page shares: view (simple or technical), language, campaign,
 * index and the selected municipality. Choosing a campaign recolours the map and highlights it in the province chart.
 */
export function Dashboard({ data }: { data: PageData }) {
  const [lang, setLang] = useState<Lang>("es");
  const [campaign, setCampaign] = useState<Campaign>(DEFAULT_CAMPAIGN);
  const [index, setIndex] = useState<IndexKey>("ndvi_spring");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [features, setFeatures] = useState<MunicipalityProperties[]>([]);
  const [theme, setTheme] = useTheme();
  const [mode, setMode] = useMode();
  const simple = mode === "simple";

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
        mode={mode}
        onMode={setMode}
        onLang={setLang}
        onTheme={setTheme}
        onCampaign={setCampaign}
        onIndex={setIndex}
      />
      <main>
        {simple ? (
          <HarvestSummary
            lang={lang}
            forecast={data.forecast}
            summary={data.summary}
            municipalities={data.municipalities}
            price={data.price}
          />
        ) : (
          <Verdict lang={lang} summary={data.summary} forecast={data.forecast} />
        )}
        <Workbench
          lang={lang}
          campaign={campaign}
          index={index}
          mode={mode}
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
          mode={mode}
          density={data.price?.oil_density_kg_per_l}
        />
        {!simple && (
          <ErrorSection
            lang={lang}
            campaign={campaign}
            production={data.production}
            scores={data.summary}
          />
        )}
        <Method lang={lang} mode={mode} onShowTechnical={() => setMode("technical")} />
      </main>
    </>
  );
}
