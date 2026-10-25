"use client";

import type { ExpressionSpecification, Map as MapLibreMap, StyleSpecification } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";

import { MAP_URL } from "@/lib/api";
import { INDEX_CAMPAIGNS, indexProperty } from "@/lib/campaigns";
import { t } from "@/lib/i18n";
import { formatIndex, rampOf, type Lang } from "@/lib/scale";
import { PALETTES, useTheme, type Theme } from "@/lib/theme";
import type { IndexKey, MunicipalityProperties } from "@/lib/types";

import styles from "./OliveMap.module.css";

/** Plain ground used when the basemap cannot be reached: the olive area still draws. */
function fallbackStyle(theme: Theme): StyleSpecification {
  const ground = PALETTES[theme].tokens["--map-ground"];
  return {
    version: 8,
    sources: {},
    layers: [{ id: "ground", type: "background", paint: { "background-color": ground } }],
  };
}
const SOURCE = "olive";
const INDEX_KEYS: IndexKey[] = ["ndvi_spring", "ndmi_summer"];

interface Props {
  lang: Lang;
  campaign: string;
  index: IndexKey;
  breaks: number[];
  selectedId: string | null;
  onFeatures: (features: MunicipalityProperties[]) => void;
  onSelect: (id: string | null) => void;
}

interface Hover {
  x: number;
  y: number;
  properties: MunicipalityProperties;
}

type Position = number[];
interface Feature {
  type: "Feature";
  id?: string;
  properties: MunicipalityProperties & Record<string, unknown>;
  geometry: { type: "Polygon" | "MultiPolygon"; coordinates: Position[][] | Position[][][] };
}

/** Paint expression: the class colour of the chosen index and campaign, grey when missing. */
function fillColour(
  index: IndexKey,
  campaign: string,
  breaks: number[],
  theme: Theme,
): ExpressionSpecification {
  const key = indexProperty(index, campaign);
  const ramp = rampOf(index, theme === "dark");
  const noData = PALETTES[theme].noData;
  if (breaks.length === 0) return ["literal", noData] as unknown as ExpressionSpecification;
  const stops = breaks.flatMap((b, i) => [b, ramp[i + 1]]);
  return [
    "case",
    ["==", ["typeof", ["get", key]], "number"],
    ["step", ["get", key], ramp[0], ...stops],
    noData,
  ] as ExpressionSpecification;
}

function bounds(geometry: Feature["geometry"]): [number, number, number, number] {
  let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
  const walk = (coords: unknown): void => {
    if (Array.isArray(coords) && typeof coords[0] === "number") {
      const [x, y] = coords as number[];
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    } else if (Array.isArray(coords)) coords.forEach(walk);
  };
  walk(geometry.coordinates);
  return [minX, minY, maxX, maxY];
}

export function OliveMap({
  lang,
  campaign,
  index,
  breaks,
  selectedId,
  onFeatures,
  onSelect,
}: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const featuresRef = useRef<Map<string, Feature>>(new Map());
  const onSelectRef = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);
  const [hover, setHover] = useState<Hover | null>(null);
  const [theme] = useTheme();
  // Latest view settings, read when a (new) basemap style finishes loading.
  const view = useRef({ index, campaign, breaks, selectedId, theme });
  const styleTheme = useRef<Theme>(theme);
  const fellBack = useRef(false);

  useEffect(() => {
    onSelectRef.current = onSelect;
    view.current = { index, campaign, breaks, selectedId, theme };
  });

  // Create the map once, load the measured olive area, flatten its indices for paint expressions.
  useEffect(() => {
    let cancelled = false;
    let map: MapLibreMap | null = null;

    (async () => {
      try {
        const [{ Map, NavigationControl, setWorkerUrl }, response] = await Promise.all([
          import("maplibre-gl"),
          fetch(MAP_URL),
        ]);
        if (!response.ok) throw new Error(`map ${response.status}`);
        const collection = (await response.json()) as { type: string; features: Feature[] };
        if (cancelled || !container.current) return;

        for (const feature of collection.features) {
          const p = feature.properties;
          const id = `${p.province_code}-${p.municipality_code}`;
          p.id = id;
          for (const c of INDEX_CAMPAIGNS)
            for (const k of INDEX_KEYS) p[indexProperty(k, c)] = p.indices[c]?.[k] ?? null;
          featuresRef.current.set(id, feature);
        }
        onFeatures(collection.features.map((f) => f.properties));

        const all = collection.features.map((f) => bounds(f.geometry));
        const extent: [number, number, number, number] = [
          Math.min(...all.map((b) => b[0])),
          Math.min(...all.map((b) => b[1])),
          Math.max(...all.map((b) => b[2])),
          Math.max(...all.map((b) => b[3])),
        ];

        setWorkerUrl("/maplibre-gl-worker.mjs");
        // Read the theme from the page itself: the first render always sees the server's "light".
        styleTheme.current = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
        map = new Map({
          container: container.current,
          style: PALETTES[styleTheme.current].basemap,
          bounds: extent,
          fitBoundsOptions: {
            // Keep the measured olive area clear of the floating legend card.
            padding:
              container.current.clientWidth < 640
                ? { top: 150, bottom: 70, left: 20, right: 20 }
                : { top: 40, bottom: 90, left: 360, right: 60 },
          },
          attributionControl: { compact: true },
          dragRotate: false,
          pitchWithRotate: false,
        });
        map.addControl(new NavigationControl({ showCompass: false }), "top-right");
        mapRef.current = map;

        // Fall back to a plain ground only when the basemap style itself cannot be loaded; a
        // failed tile, sprite or glyph (errors that carry a sourceId or happen after the style
        // loaded) must not throw the basemap away for the rest of the visit.
        map.on("error", (event) => {
          const fromSource = "sourceId" in event && Boolean(event.sourceId);
          if (map && !fellBack.current && !fromSource && !map.isStyleLoaded()) {
            fellBack.current = true;
            map.setStyle(fallbackStyle(styleTheme.current));
          }
        });

        let listening = false;
        // Runs for the first basemap and again after every theme switch (setStyle drops layers).
        map.on("style.load", () => {
          if (!map || map.getSource(SOURCE)) return;
          const palette = PALETTES[styleTheme.current];
          const current = view.current;
          map.addSource(SOURCE, {
            type: "geojson",
            data: collection as unknown as GeoJSON.FeatureCollection,
            promoteId: "id",
          });
          map.addLayer({
            id: "olive-fill",
            type: "fill",
            source: SOURCE,
            paint: {
              "fill-color": fillColour(
                current.index,
                current.campaign,
                current.breaks,
                styleTheme.current,
              ),
              "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 1, 0.88],
            },
          });
          map.addLayer({
            id: "olive-line",
            type: "line",
            source: SOURCE,
            paint: { "line-color": palette.outline, "line-opacity": 0.35, "line-width": 0.4 },
          });
          map.addLayer({
            id: "olive-selected",
            type: "line",
            source: SOURCE,
            filter: ["==", ["get", "id"], current.selectedId ?? ""],
            paint: { "line-color": palette.selected, "line-width": 2.2 },
          });
          setReady(true);
          if (listening) return;
          listening = true;

          let hovered: string | null = null;
          map.on("mousemove", "olive-fill", (event) => {
            const feature = event.features?.[0];
            if (!map || !feature) return;
            const id = String(feature.properties?.id);
            if (hovered && hovered !== id)
              map.setFeatureState({ source: SOURCE, id: hovered }, { hover: false });
            hovered = id;
            map.setFeatureState({ source: SOURCE, id }, { hover: true });
            map.getCanvas().style.cursor = "pointer";
            const properties = featuresRef.current.get(id)?.properties;
            if (properties) setHover({ x: event.point.x, y: event.point.y, properties });
          });
          map.on("mouseleave", "olive-fill", () => {
            if (map && hovered)
              map.setFeatureState({ source: SOURCE, id: hovered }, { hover: false });
            hovered = null;
            if (map) map.getCanvas().style.cursor = "";
            setHover(null);
          });
          map.on("click", "olive-fill", (event) => {
            const id = event.features?.[0]?.properties?.id;
            if (id) onSelectRef.current(String(id));
          });
        });
      } catch {
        if (!cancelled) setError(true);
      }
    })();

    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
    // The map is created once; later changes go through the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Signature move: campaign or index changes recolour the measured olive area.
  useEffect(() => {
    const map = mapRef.current;
    // During a theme switch the old layers are about to be replaced: style.load paints the new ones.
    if (!ready || !map || !map.getLayer("olive-fill") || styleTheme.current !== theme) return;
    map.setPaintProperty("olive-fill", "fill-color", fillColour(index, campaign, breaks, theme));
  }, [ready, index, campaign, breaks, theme]);

  // Theme switch: swap the basemap; "style.load" adds the olive layers back in the new colours.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || styleTheme.current === theme) return;
    styleTheme.current = theme;
    map.setStyle(fellBack.current ? fallbackStyle(theme) : PALETTES[theme].basemap);
  }, [ready, theme]);

  // Outline the selected municipality and bring it into view.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !map.getSource(SOURCE)) return;
    map.setFilter("olive-selected", ["==", ["get", "id"], selectedId ?? ""]);
    const feature = selectedId ? featuresRef.current.get(selectedId) : undefined;
    if (feature) {
      const [w, s, e, n] = bounds(feature.geometry);
      map.fitBounds([w, s, e, n], {
        padding: { top: 80, bottom: 280, left: 80, right: 80 },
        maxZoom: 11,
        duration: 700,
      });
    }
  }, [ready, selectedId]);

  const hovered = hover?.properties;
  const hoveredValue = hovered ? (hovered.indices[campaign]?.[index] ?? null) : null;

  return (
    <div className={styles.wrap}>
      <div ref={container} className={styles.map} />
      {!ready && !error && <p className={styles.status}>{t(lang, "loadingMap")}</p>}
      {error && (
        <p className={styles.status} role="alert">
          {t(lang, "mapError")}
        </p>
      )}
      {hover && hovered && (
        <div className={styles.tooltip} style={{ left: hover.x, top: hover.y }} role="presentation">
          <strong>{hovered.name}</strong>
          <span className="num">
            {index === "ndvi_spring" ? "NDVI" : "NDMI"} {campaign}:{" "}
            {hoveredValue === null ? t(lang, "noData") : formatIndex(hoveredValue, lang)}
          </span>
        </div>
      )}
    </div>
  );
}
