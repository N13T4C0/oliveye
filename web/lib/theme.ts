/**
 * Light and dark themes.
 *
 * CSS components read the tokens in app/globals.css. The map (WebGL paint properties) cannot read
 * CSS variables, and Recharts takes colours as SVG attributes, so both take the same colours from
 * `PALETTES`; lib/theme.test.ts checks both lists stay identical. (Server HTML is rendered with
 * the light palette; charts switch to dark on the first client render after hydration.)
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
let stopWatching: (() => void) | null = null;

function current(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function savedTheme(): Theme | null {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    return saved === "light" || saved === "dark" ? saved : null;
  } catch {
    return null;
  }
}

function apply(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  listeners.forEach((listener) => listener());
}

/**
 * One set of window listeners for the whole page, however many components use the theme:
 * follow the system setting until the visitor picks a theme, and follow other tabs' choices.
 */
function watch(): () => void {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onSystem = () => {
    if (savedTheme() === null) apply(media.matches ? "dark" : "light");
  };
  const onStorage = (event: StorageEvent) => {
    if (event.key === THEME_STORAGE_KEY) apply(savedTheme() ?? (media.matches ? "dark" : "light"));
  };
  media.addEventListener("change", onSystem);
  window.addEventListener("storage", onStorage);
  return () => {
    media.removeEventListener("change", onSystem);
    window.removeEventListener("storage", onStorage);
  };
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  stopWatching ??= watch();
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && stopWatching) {
      stopWatching();
      stopWatching = null;
    }
  };
}

/** Current theme and a setter that remembers the choice (light on the server). */
export function useTheme(): [Theme, (theme: Theme) => void] {
  const theme = useSyncExternalStore(subscribe, current, () => "light" as Theme);
  const setTheme = useCallback((next: Theme) => {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Private mode or blocked storage: the choice simply lasts for this page view.
    }
    apply(next);
  }, []);
  return [theme, setTheme];
}
