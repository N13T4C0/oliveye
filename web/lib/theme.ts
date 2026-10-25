/**
 * Light and dark themes.
 *
 * CSS components read the tokens in app/globals.css. Charts (SVG attributes) and the map (WebGL
 * paint properties) cannot read CSS variables, so they take the same colours from `PALETTES`;
 * lib/theme.test.ts checks both lists stay identical.
 */

import { useCallback, useSyncExternalStore } from "react";

import { THEME_STORAGE_KEY } from "./theme-boot";

export type Theme = "light" | "dark";

export interface Palette {
  /** CSS tokens mirrored here (name in globals.css → value). */
  tokens: {
    "--ink-strong": string;
    "--spruce": string;
    "--signal": string;
    "--paper": string;
    "--fog": string;
    "--rule": string;
    "--muted": string;
    "--hairline": string;
    "--alarm": string;
    "--tooltip": string;
    "--map-ground": string;
  };
  /** Map-only colours. */
  noData: string;
  outline: string;
  selected: string;
  basemap: string;
}

export const PALETTES: Record<Theme, Palette> = {
  light: {
    tokens: {
      "--ink-strong": "#0e0f0c",
      "--spruce": "#054d28",
      "--signal": "#0b4c72",
      "--paper": "#ffffff",
      "--fog": "#e8ebe6",
      "--rule": "#d6dad3",
      "--muted": "#6a6c6a",
      "--hairline": "#868685",
      "--alarm": "#cb272f",
      "--tooltip": "#0e0f0c",
      "--map-ground": "#f2f3ef",
    },
    noData: "#e8ebe6",
    outline: "#163300",
    selected: "#0e0f0c",
    basemap: "https://tiles.openfreemap.org/styles/positron",
  },
  dark: {
    tokens: {
      "--ink-strong": "#f1f8ec",
      "--spruce": "#7ccf8a",
      "--signal": "#6cb2dd",
      "--paper": "#0e0f0c",
      "--fog": "#1c2318",
      "--rule": "#2c3427",
      "--muted": "#9ba596",
      "--hairline": "#6f786a",
      "--alarm": "#ff7a7a",
      "--tooltip": "#24301d",
      "--map-ground": "#1a1e17",
    },
    noData: "#3a4036",
    outline: "#e2f6d5",
    selected: "#ffffff",
    basemap: "https://tiles.openfreemap.org/styles/dark",
  },
};

/** Chart colours by role, so components never pick hex values themselves. */
export function chartColours(theme: Theme) {
  const t = PALETTES[theme].tokens;
  return {
    grid: t["--fog"],
    axis: t["--rule"],
    tick: t["--muted"],
    cursor: t["--hairline"],
    real: t["--ink-strong"],
    halo: t["--paper"],
    oliveye: t["--spruce"],
    aforo: t["--signal"],
    highlight: "#9fe870",
    tooltip: {
      borderRadius: 10,
      border: `1px solid ${t["--rule"]}`,
      background: t["--paper"],
      color: t["--ink-strong"],
      fontSize: 13,
    },
  };
}

const listeners = new Set<() => void>();

function current(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  // Follow the system setting until the visitor picks a theme explicitly.
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onSystem = () => {
    let saved: string | null = null;
    try {
      saved = localStorage.getItem(THEME_STORAGE_KEY);
    } catch {
      saved = null;
    }
    if (saved !== "light" && saved !== "dark") {
      document.documentElement.dataset.theme = media.matches ? "dark" : "light";
      listeners.forEach((l) => l());
    }
  };
  media.addEventListener("change", onSystem);
  return () => {
    listeners.delete(listener);
    media.removeEventListener("change", onSystem);
  };
}

/** Current theme and a setter that remembers the choice (light on the server). */
export function useTheme(): [Theme, (theme: Theme) => void] {
  const theme = useSyncExternalStore(subscribe, current, () => "light" as Theme);
  const setTheme = useCallback((next: Theme) => {
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Private mode or blocked storage: the choice simply lasts for this page view.
    }
    listeners.forEach((l) => l());
  }, []);
  return [theme, setTheme];
}
