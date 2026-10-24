"""Read-only HTTP API over the exported OlivEye results (Phase 4 groundwork).

Data comes from CSV files in a data directory (`OLIVEYE_DATA_DIR`, produced by
`scripts/export_api_data.py`); a PostGIS backend can replace the loader later without changing
the endpoints.

Run locally:

    OLIVEYE_DATA_DIR=data/processed/api uv run uvicorn oliveye.api.app:app --reload
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


class Municipality(BaseModel):
    province_code: str
    municipality_code: str
    name: str
    olive_hectares: float
    processed: bool


class MonthlyIndex(BaseModel):
    month: str
    ndvi: float | None
    ndmi: float | None
    valid_cells: int | None


class ProductionPoint(BaseModel):
    campaign: str
    oil_final_t: float | None
    oil_aforo_t: float | None
    pred_t: float | None


class ModelScore(BaseModel):
    model: str
    rows: int
    mape_pct: float | None
    wins_vs_aforo: int


def _read(path: Path, **kwargs: object) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing API data file: {path}")
    frame: pd.DataFrame = pd.read_csv(path, **kwargs)  # type: ignore[call-overload]
    cleaned: pd.DataFrame = frame.astype(object).where(frame.notna(), None)
    return cleaned


def create_app(data_dir: Path) -> FastAPI:
    """Build the app over one data directory (loaded once, at start-up)."""
    codes = {"province_code": str, "municipality_code": str}
    municipalities = _read(data_dir / "municipalities.csv", dtype=codes)
    indices = _read(data_dir / "indices_monthly.csv", dtype={**codes, "month": str})
    production = _read(data_dir / "production.csv")
    summary = _read(data_dir / "summary.csv")

    app = FastAPI(
        title="OlivEye API",
        description="Olive grove indices and olive oil production estimates for Jaén and Granada.",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/municipalities", response_model=list[Municipality])
    def list_municipalities(
        province: str | None = Query(default=None, description="INE province code, e.g. 23"),
    ) -> list[dict[str, object]]:
        rows = municipalities
        if province is not None:
            rows = rows[rows["province_code"] == province]
        return rows.to_dict("records")  # type: ignore[return-value]

    @app.get("/municipalities/{province}/{municipality}/indices", response_model=list[MonthlyIndex])
    def municipality_indices(province: str, municipality: str) -> list[dict[str, object]]:
        rows = indices[
            (indices["province_code"] == province) & (indices["municipality_code"] == municipality)
        ]
        if rows.empty:
            raise HTTPException(status_code=404, detail="No indices for this municipality")
        return rows.sort_values("month").to_dict("records")  # type: ignore[return-value]

    @app.get("/provinces/{province}/production", response_model=list[ProductionPoint])
    def province_production(province: str) -> list[dict[str, object]]:
        rows = production[production["province"] == province]
        if rows.empty:
            raise HTTPException(status_code=404, detail="Unknown province")
        return rows.sort_values("campaign").to_dict("records")  # type: ignore[return-value]

    @app.get("/models/summary", response_model=list[ModelScore])
    def model_summary() -> list[dict[str, object]]:
        return summary.to_dict("records")  # type: ignore[return-value]

    return app


def _default_app() -> FastAPI:
    data_dir = Path(os.environ.get("OLIVEYE_DATA_DIR", "data/processed/api"))
    if not data_dir.exists():
        # Import-time safety: an empty app that explains what is missing.
        fallback = FastAPI(title="OlivEye API (no data)")

        @fallback.get("/health")
        def health() -> dict[str, str]:
            return {"status": f"no data directory at {data_dir}"}

        return fallback
    return create_app(data_dir)


app = _default_app()
