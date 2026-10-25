// MapLibre parses map data in a Web Worker loaded from its own file. Bundlers do not ship that
// file, so it is copied to public/ before dev and build (and kept out of git).
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const dist = dirname(require.resolve("maplibre-gl/package.json"));
mkdirSync("public", { recursive: true });
copyFileSync(
  join(dist, "dist", "maplibre-gl-worker.mjs"),
  join("public", "maplibre-gl-worker.mjs"),
);
console.log("copied maplibre-gl-worker.mjs to public/");
