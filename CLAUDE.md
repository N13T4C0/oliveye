# CLAUDE.md — OlivEye

Context and rules for AI assistants (and humans) working on this repository.

## What this project is

**OlivEye** estimates olive oil production per province in Andalusia (focus: **Jaén** and **Granada**)
from Sentinel-2 imagery, climate data and historical production, and compares the prediction with
the official harvest forecast (*aforo*) published by the Junta de Andalucía.

Pipeline at a glance:

```
SIGPAC olive parcels ──► Sentinel-2 indices (NDVI, NDMI) via openEO / CDSE ──┐
Climate (RIA / AEMET) ───────────────────────────────────────────────────────┼─► features per province & campaign
Historical production (Junta, AICA) ─────────────────────────────────────────┘
        ──► models (baseline, Ridge, XGBoost; leave-one-campaign-out) ──► FastAPI ──► Next.js + MapLibre
```

Key constraint: only ~10 campaigns since 2015 (Sentinel-2 era). **Honest validation and simple
models beat complexity.** Never report metrics that were not computed with leave-one-campaign-out.

## Stack

| Layer | Tools |
|---|---|
| Earth observation | openEO (Copernicus Data Space Ecosystem), Sentinel-2 L2A |
| Geodata | GeoPandas, Shapely, rasterio, xarray |
| Big data / ETL | PySpark (Phase 2) |
| Storage | PostgreSQL 17 + PostGIS 3.5 (Docker) |
| ML | scikit-learn, XGBoost, MLflow |
| API | FastAPI |
| Web | Next.js + TypeScript + MapLibre GL |
| Tooling | uv, ruff, mypy, pytest, Docker, GitHub Actions |

## Repository layout

```
data/            # local data, NEVER committed (raw/, interim/, processed/, cache/)
notebooks/       # numbered exploration notebooks: 01_..., 02_...
src/oliveye/     # installable Python package
  pipeline/      #   ETL: SIGPAC, openEO extraction, climate, production
  models/        #   features, training, evaluation
  db/            #   PostGIS access helpers
api/             # FastAPI service (Phase 4)
web/             # Next.js + MapLibre frontend (Phase 5)
db/init/         # SQL run once when the PostGIS container is created
scripts/         # one-off CLI scripts (downloads, backfills)
tests/           # pytest
docs/            # decisions (ADRs), methodology notes, figures for the README
```

## Conventions

### Language
- Code, identifiers, comments, docstrings and commit messages: **English**.
- Conversation with the author and user-facing docs can be in Spanish.

### Python
- Python 3.12. Dependencies managed with **uv** (`pyproject.toml` + `uv.lock`).
- **Type hints everywhere** (functions, return values, dataclasses). `mypy --strict` on `src/`.
- Formatting and linting with **ruff** (`ruff format`, `ruff check`).
- Prefer pure functions in `src/oliveye/`; notebooks only orchestrate and plot, they import from the package.
- CRS discipline: store geometries in **EPSG:4326** in PostGIS; compute areas/buffers in
  **EPSG:25830** (ETRS89 / UTM 30N, the official CRS for mainland Spain). Always state the CRS explicitly.
- Paths via `pathlib.Path`, never hard-coded absolute paths.

### TypeScript (Phase 5)
- `strict: true`, no `any`. ESLint + Prettier.

### Git
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `perf:`, `ci:`.
  Optional scope: `feat(pipeline): add NDVI aggregation per parcel`.
- Small, focused commits. Imperative mood, ≤ 72 chars in the subject.
- **Do not add `Co-Authored-By:` or `Claude-Session` trailers to commit messages.**
- Never commit `data/`, `.env`, credentials, notebooks with huge outputs (clear outputs or keep them small).

## Copernicus free-quota rules (IMPORTANT)

openEO on CDSE has a **monthly free credit allowance** (10,000 credits/month at the time of
writing; check the balance in the openEO Algorithm Plaza → *Billing*). Synchronous requests cost a
fixed few credits each; batch jobs are billed by resources used. Rules:

1. **Aggregate remotely.** Use `aggregate_spatial` (per parcel or per province) and temporal
   compositing *on the server*. Download time series as CSV/JSON/Parquet, **not raster cubes**.
2. **Mask clouds remotely** (SCL band) before aggregating, so we never download useless pixels.
3. **Cache everything.** Every result lands in `data/cache/openeo/` with a deterministic name
   (hash of collection + bbox/geometry + dates + bands + process). Before any request, check the cache.
4. **Prototype small.** Develop with 1–5 parcels and 1–3 months; scale up only when the code works.
5. **Prefer one batch job over many sync requests** when processing many parcels/dates.
6. **Load only the bands you need** (e.g. B04, B08, B11, SCL) and set tight spatial/temporal extents.
7. Log the credits used per job (response header `Openeo-Costs-Experimental` / job metadata)
   in `data/cache/openeo/credits_log.csv`.
8. Never put openEO requests inside loops without the cache check.

## Automation (how the assistant works unattended)

- Networked or credentialed work runs through the **job queue**: add `jobs/<YYYY-MM-DD-name>.json`,
  push to `main`, read the outcome on the `results` branch. Full guide: `docs/automation.md`.
- openEO jobs are **dry runs by default**. Review the dry run before any real run, and check
  `_cache/openeo/credits_log.csv` on the results branch after it.
- Subagents for this repo live in `.claude/agents/` (selected from agency-agents, MIT). Use
  `code-reviewer` before committing non-trivial changes and `model-qa`/`statistician` before
  publishing any metric.

## Common commands

```bash
# Environment
uv sync                              # create .venv and install dependencies
uv run jupyter lab                   # start notebooks
uv run python -c "import openeo; openeo.connect('openeo.dataspace.copernicus.eu').authenticate_oidc()"

# Database
cp .env.example .env                 # then edit the password
docker compose up -d                 # start PostgreSQL + PostGIS
docker compose ps                    # check health
docker compose exec db psql -U oliveye -d oliveye -c "SELECT postgis_full_version();"
docker compose down                  # stop (data persists in the volume)

# Quality
uv run ruff format . && uv run ruff check .
uv run mypy src
uv run pytest
```
