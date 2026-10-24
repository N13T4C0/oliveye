# OlivEye API

Read-only FastAPI service over the exported results. Code: `src/oliveye/api/app.py`.

```bash
# 1. Export the data the API serves (from a checkout of the results branch + a model run)
uv run python scripts/export_api_data.py --results-dir ../oliveye-results \
    --model-run data/processed/model_run --out data/processed/api
# 2. Run it
OLIVEYE_DATA_DIR=data/processed/api uv run uvicorn oliveye.api.app:app --reload
# 3. Docs at http://127.0.0.1:8000/docs
```

| Endpoint | Returns |
|---|---|
| `GET /health` | status |
| `GET /municipalities?province=23` | municipalities with olive hectares and whether they are processed |
| `GET /municipalities/{province}/{municipality}/indices` | monthly NDVI / NDMI (outliers removed) |
| `GET /provinces/{province}/production` | final production, aforo and model prediction per campaign |
| `GET /models/summary` | leave-one-campaign-out scores |

CSV files today; a PostGIS loader can replace them without changing the endpoints.
