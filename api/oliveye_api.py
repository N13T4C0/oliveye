"""OlivEye read-only API: olive grove indices and olive oil production estimates.

Designed to run as a serverless function (Vercel): it only reads small JSON files prepared by
`scripts/export_api_data.py` (the heavy lifting happens there, once), so cold starts are fast
and the bundle is tiny. Every response is cacheable, so the CDN answers most requests without
running Python at all.

Run locally:

    uv run uvicorn app:app --app-dir api --reload      # docs at http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Data changes once a year: browsers keep it 1 h, the CDN 1 day (and serves stale while it
# refreshes in the background).
CACHE_CONTROL = "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800"


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
    target_method: str | None


class ModelScore(BaseModel):
    model: str
    rows: int
    campaigns: int
    mape_pct: float | None
    campaign_wins_vs_aforo: int
    p_vs_aforo: float | None


class CampaignError(BaseModel):
    province: str
    campaign: str
    oil_final_t: float
    pred_t: float
    oil_aforo_t: float | None
    error_pct: float
    aforo_error_pct: float | None
    closer: Literal["oliveye", "aforo", "tie"] | None
    like_for_like: bool
    target_method: str | None


class ReferencePrice(BaseModel):
    week_start: str
    week_end: str
    eur_per_kg: dict[str, float]
    low_eur_per_kg: float
    high_eur_per_kg: float
    source: str
    source_url: str
    oil_density_kg_per_l: float


class ForecastRow(BaseModel):
    province: str
    pred_t: float
    low_t: float
    high_t: float
    oil_aforo_t: float | None


class Forecast(BaseModel):
    campaign: str
    published: str
    interval_factor: float
    rows: list[ForecastRow]


def _load(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing API data file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def campaign_errors(production: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Signed % error of OlivEye and of the aforo against the final production, per campaign.

    Only rows with an OlivEye estimate (made leave-one-campaign-out) and a final figure. Rows
    without an aforo are kept but flagged `like_for_like: false`: the published MAPE compares the
    two only on rows that have both. Positive error = the estimate was above the harvest.

    The web page recomputes the same numbers from /provinces/*/production on purpose (it is
    rendered statically, without an extra request); tests keep both equal to /models/summary.
    """
    rows: list[dict[str, Any]] = []
    for province, series in sorted(production.items()):
        for point in series:
            final, pred, aforo = point["oil_final_t"], point["pred_t"], point["oil_aforo_t"]
            if final is None or pred is None or final <= 0:
                continue
            error = 100 * (pred - final) / final
            aforo_error = None if aforo is None else 100 * (aforo - final) / final
            closer = None
            if aforo_error is not None:
                gap = abs(error) - abs(aforo_error)
                closer = "oliveye" if gap < 0 else "aforo" if gap > 0 else "tie"
            rows.append(
                {
                    "province": province,
                    "campaign": point["campaign"],
                    "oil_final_t": final,
                    "pred_t": pred,
                    "oil_aforo_t": aforo,
                    "error_pct": round(error, 2),
                    "aforo_error_pct": None if aforo_error is None else round(aforo_error, 2),
                    "closer": closer,
                    "like_for_like": aforo_error is not None,
                    # "derived_from_aforo": back-calculated from the Junta's published variations
                    "target_method": point.get("target_method"),
                }
            )
    return rows


def create_app(data_dir: Path) -> FastAPI:
    """Build the app over one data directory (files are read once, at start-up)."""
    municipalities: list[dict[str, Any]] = _load(data_dir / "municipalities.json")
    indices: dict[str, list[dict[str, Any]]] = _load(data_dir / "indices.json")
    production: dict[str, list[dict[str, Any]]] = _load(data_dir / "production.json")
    summary: list[dict[str, Any]] = _load(data_dir / "summary.json")
    forecast: dict[str, Any] = _load(data_dir / "forecast.json")
    olive_map: dict[str, Any] = _load(data_dir / "map.geojson")
    prices_path = data_dir / "prices.json"
    prices: dict[str, Any] | None = _load(prices_path) if prices_path.exists() else None

    app = FastAPI(
        title="OlivEye API",
        description=(
            "Sentinel-2 olive grove indices (NDVI, NDMI) for 86 municipalities of Jaén and "
            "Granada, and olive oil production: official aforo, final figures and the OlivEye "
            "model (leave-one-campaign-out). Read-only."
        ),
        version="1.0.0",
    )
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

    @app.middleware("http")
    async def cache_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if request.method == "GET" and response.status_code == 200:
            response.headers["Cache-Control"] = CACHE_CONTROL
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/municipalities", response_model=list[Municipality])
    def list_municipalities(
        province: str | None = Query(default=None, description="INE province code: 23 or 18"),
    ) -> list[dict[str, Any]]:
        if province is None:
            return municipalities
        return [m for m in municipalities if m["province_code"] == province]

    @app.get("/municipalities/{province}/{municipality}/indices", response_model=list[MonthlyIndex])
    def municipality_indices(province: str, municipality: str) -> list[dict[str, Any]]:
        series = indices.get(f"{province}-{municipality}")
        if series is None:
            raise HTTPException(status_code=404, detail="No indices for this municipality")
        return series

    @app.get("/provinces/{province}/production", response_model=list[ProductionPoint])
    def province_production(province: str) -> list[dict[str, Any]]:
        series = production.get(province)
        if series is None:
            raise HTTPException(status_code=404, detail="Unknown province (Jaén or Granada)")
        return series

    @app.get("/models/summary", response_model=list[ModelScore])
    def model_summary() -> list[dict[str, Any]]:
        return summary

    errors = campaign_errors(production)

    @app.get("/models/errors", response_model=list[CampaignError])
    def model_errors() -> list[dict[str, Any]]:
        """OlivEye vs aforo error per province and campaign (leave-one-campaign-out estimates)."""
        return errors

    @app.get("/prices/reference", response_model=ReferencePrice)
    def reference_price() -> dict[str, Any]:
        """Dated Poolred origin price per oil category (EUR/kg), for an approximate value."""
        if prices is None:
            raise HTTPException(status_code=404, detail="No reference price published")
        return prices

    @app.get("/forecast", response_model=Forecast)
    def dated_forecast() -> dict[str, Any]:
        return forecast

    @app.get("/map/municipalities")
    def map_municipalities() -> dict[str, Any]:
        """GeoJSON (EPSG:4326): each municipality's measured olive area with seasonal indices."""
        return olive_map

    return app
