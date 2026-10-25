/**
 * Simple (default, plain language for growers) or technical view (NDVI, NDMI, MAPE...).
 * Remembered per browser; the server always renders the simple view.
 */

import { useCallback, useSyncExternalStore } from "react";

export type Mode = "simple" | "technical";

const STORAGE_KEY = "oliveye-mode";
const listeners = new Set<() => void>();

function read(): Mode {
  try {
    return localStorage.getItem(STORAGE_KEY) === "technical" ? "technical" : "simple";
  } catch {
    return "simple";
  }
}

let current: Mode | null = null;

function snapshot(): Mode {
  current ??= read();
  return current;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useMode(): [Mode, (mode: Mode) => void] {
  const mode = useSyncExternalStore(subscribe, snapshot, () => "simple" as Mode);
  const setMode = useCallback((next: Mode) => {
    current = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage blocked: the choice lasts for this page view.
    }
    listeners.forEach((listener) => listener());
  }, []);
  return [mode, setMode];
}
