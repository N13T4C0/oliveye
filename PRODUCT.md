# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js (App Router) + TypeScript strict + MapLibre GL, deployed on Vercel; data from the
OlivEye FastAPI (`api/`, also on Vercel). Decided by the author (ADR 0005).

## Users

Two audiences, served equally (author's answer):

- **Evaluators** — recruiters and data/AI engineers judging the author's work in a few minutes:
  they need to grasp the question, the result and the rigour quickly.
- **Olive sector** — farmers, cooperatives and agricultural technicians in Jaén and Granada who
  want to look up their municipality's olive grove signal and the campaign forecast.

Desktop first, but the link is shared from a CV/LinkedIn, so it must work well on mobile.

## Product Purpose

Show, for the provinces of Jaén and Granada, what Sentinel-2 satellite imagery says about the
olive groves (NDVI vigour, NDMI water) per municipality since 2016, and how a simple, honestly
validated model's production estimate compares with the official harvest forecast (*aforo*) of
the Junta de Andalucía. Success: a visitor understands the question, the honest answer ("not
yet: the aforo, with field counts, is ~3–4× more accurate") and can explore the data.

## Positioning

An end-to-end, reproducible pipeline from raw satellite data to a public product, built by one
junior developer, that reports a negative result honestly (leave-one-campaign-out, like-for-like
baselines, dated out-of-sample forecast) instead of a flattering metric.

## Operating Context

- Visitors arrive from a CV, LinkedIn or GitHub link; evaluators skim, sector users explore.
- Data changes about once a year (a new campaign and aforo in October).
- Data sources must be cited under every chart: Copernicus Sentinel-2 via openEO (CDSE), SIGPAC,
  ERA5 via Open-Meteo, Junta de Andalucía aforo, AICA.

## Capabilities and Constraints

- 86 municipalities processed (~80 % of each province's SIGPAC olive area); 269 listed.
- Monthly NDVI/NDMI 2016-10 → 2026-09; seasonal indices per campaign from 2017/18.
- Production per province: final figures (15 of 16 derived from aforo variations, ADR 0002),
  aforo, out-of-sample model predictions 2017/18–2025/26, dated forecast 2026/27 with ×/÷2 interval.
- Map geometry is the measured olive area (dissolved 250 m cells), not municipal boundaries.
- Spanish first with an English toggle (author's answer).
- Terminology: "aforo oficial", "producción final", "estimación OlivEye", "campaña 2025/26".

## Brand Commitments

- Name: OlivEye. Visual system already defined in `DESIGN.md` (author approved).
- Results wording must match `docs/results/README.md` (reviewed by model-qa and the auditor):
  never present the model as better than the aforo, always show the baseline and validation.

## Evidence on Hand

- `api/data/*.json` (published data), `docs/results/` (reviewed metrics, figures),
  `docs/results/forecast-2026-27.md` (dated forecast and caveats), ADRs 0001–0005.
- No testimonials, users, press or partnerships exist: never invent them.

## Product Principles

1. Honesty over flattery: every number with its baseline, validation scheme and caveat.
2. The data is the interface: map and charts first, prose only where it explains.
3. Explain remote sensing in plain words the first time (NDVI, NDMI, aforo).
4. Cite sources and dates under every chart.
5. Fast and light on a phone: small payloads, cached responses.

## Accessibility & Inclusion

WCAG 2.2 AA: colour never carries meaning alone (labels, line styles, markers), colour-blind safe
palettes (validated), keyboard access to the map's municipalities and controls, a table view for
every chart.
