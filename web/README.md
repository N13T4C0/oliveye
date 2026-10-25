# OlivEye web

Next.js (App Router, TypeScript strict) + MapLibre GL + Recharts. One page, Spanish first with
an English toggle, deployed on Vercel as its own project (**Root Directory `web/`**, ADR 0005).
Design system: [`../DESIGN.md`](../DESIGN.md); product context: [`../PRODUCT.md`](../PRODUCT.md).

```bash
npm install
# The API must be reachable (deployed, or locally: uv run uvicorn app:app --app-dir api --port 8000)
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev     # http://localhost:3000
npm test            # vitest: scales, formatting, i18n, list and chart helpers
npm run lint && npm run typecheck && npm run format:check
```

| Path                             | Role                                                                                |
| -------------------------------- | ----------------------------------------------------------------------------------- |
| `app/page.tsx`                   | server component: fetches the small JSON once a day (`revalidate: 1d`)              |
| `components/Dashboard.tsx`       | shared state: language, campaign, index, selected municipality                      |
| `components/OliveMap.tsx`        | MapLibre map of the measured olive area (GeoJSON straight from the API, CDN-cached) |
| `components/SeriesPanel.tsx`     | monthly NDVI/NDMI of the selected municipality, campaign window highlighted         |
| `components/ProvinceSection.tsx` | real production vs aforo vs OlivEye, 2026/27 forecast with its interval, table view |
| `lib/`                           | API client, types, colour scales, formatting, campaign helpers, ES/EN copy          |

`NEXT_PUBLIC_API_URL` is the only setting. MapLibre's worker file is copied to `public/` by the
`predev`/`prebuild` scripts. If the basemap cannot load, the map falls back to a plain ground and
still draws the olive area.
