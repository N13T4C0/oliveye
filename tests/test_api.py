"""Tests for the deployable read-only API (api/oliveye_api.py) over exported JSON files."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from oliveye_api import create_app


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    _write(
        tmp_path / "municipalities.json",
        [
            {
                "province_code": "23",
                "municipality_code": "60",
                "name": "Martos",
                "olive_hectares": 21796.4,
                "processed": True,
            },
            {
                "province_code": "23",
                "municipality_code": "92",
                "name": "Úbeda",
                "olive_hectares": 30559.9,
                "processed": False,
            },
            {
                "province_code": "18",
                "municipality_code": "104",
                "name": "Loja",
                "olive_hectares": 9000.0,
                "processed": True,
            },
        ],
    )
    _write(
        tmp_path / "indices.json",
        {
            "23-60": [
                {"month": "2025-07", "ndvi": 0.271, "ndmi": -0.068, "valid_cells": 3130},
                {"month": "2025-08", "ndvi": 0.260, "ndmi": None, "valid_cells": 3130},
            ]
        },
    )
    _write(
        tmp_path / "production.json",
        {
            "Jaén": [
                {
                    "campaign": "2024/25",
                    "oil_final_t": 560800.0,
                    "oil_aforo_t": 445000.0,
                    "pred_t": 500000.0,
                    "target_method": "derived_from_aforo",
                },
                {
                    "campaign": "2025/26",
                    "oil_final_t": 389000.0,
                    "oil_aforo_t": 475000.0,
                    "pred_t": None,
                    "target_method": "derived_from_aforo",
                },
            ]
        },
    )
    _write(
        tmp_path / "summary.json",
        [
            {
                "model": "aforo",
                "rows": 15,
                "campaigns": 9,
                "mape_pct": 11.9,
                "campaign_wins_vs_aforo": 0,
                "p_vs_aforo": None,
            },
            {
                "model": "ridge",
                "rows": 15,
                "campaigns": 9,
                "mape_pct": 44.1,
                "campaign_wins_vs_aforo": 3,
                "p_vs_aforo": 0.055,
            },
        ],
    )
    _write(
        tmp_path / "forecast.json",
        {
            "campaign": "2026/27",
            "published": "2026-10-25",
            "interval_factor": 2.0,
            "rows": [
                {
                    "province": "Jaén",
                    "pred_t": 392348.0,
                    "low_t": 196140.0,
                    "high_t": 784835.0,
                    "oil_aforo_t": 575000.0,
                }
            ],
        },
    )
    _write(
        tmp_path / "map.geojson",
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"province_code": "23", "municipality_code": "60"},
                    "geometry": {"type": "Point", "coordinates": [-3.97, 37.72]},
                }
            ],
        },
    )
    return TestClient(create_app(tmp_path))


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_municipalities_filtered_by_province(client: TestClient) -> None:
    response = client.get("/municipalities", params={"province": "23"})

    assert response.status_code == 200
    assert [m["name"] for m in response.json()] == ["Martos", "Úbeda"]


def test_monthly_indices_of_a_municipality(client: TestClient) -> None:
    body = client.get("/municipalities/23/60/indices").json()

    assert [row["month"] for row in body] == ["2025-07", "2025-08"]
    assert body[0]["ndvi"] == pytest.approx(0.271)
    assert body[1]["ndmi"] is None  # a masked month stays empty, never invented


def test_unknown_municipality_is_404(client: TestClient) -> None:
    assert client.get("/municipalities/23/999/indices").status_code == 404


def test_province_production_series(client: TestClient) -> None:
    body = client.get("/provinces/Jaén/production").json()

    assert body[0]["campaign"] == "2024/25"
    assert body[0]["target_method"] == "derived_from_aforo"
    assert body[1]["pred_t"] is None
    assert client.get("/provinces/Sevilla/production").status_code == 404


def test_model_summary_and_forecast(client: TestClient) -> None:
    summary = client.get("/models/summary").json()
    assert {row["model"] for row in summary} == {"aforo", "ridge"}

    forecast = client.get("/forecast").json()
    assert forecast["campaign"] == "2026/27"
    assert forecast["rows"][0]["low_t"] < forecast["rows"][0]["pred_t"]


def test_map_is_geojson(client: TestClient) -> None:
    response = client.get("/map/municipalities")

    assert response.status_code == 200
    assert response.json()["type"] == "FeatureCollection"


def test_responses_are_cacheable_and_open_to_browsers(client: TestClient) -> None:
    response = client.get("/models/summary", headers={"Origin": "https://example.org"})

    assert "s-maxage" in response.headers["cache-control"]
    assert response.headers["access-control-allow-origin"] == "*"


def test_campaign_errors_reproduce_the_published_mape() -> None:
    """The per-campaign errors must add up to the MAPE published in /models/summary."""
    data = Path(__file__).resolve().parents[1] / "api" / "data"
    published = TestClient(create_app(data))
    errors = published.get("/models/errors").json()
    summary = {row["model"]: row for row in published.get("/models/summary").json()}

    common = [row for row in errors if row["like_for_like"]]
    assert len(common) == summary["ridge"]["rows"]
    mape = sum(abs(row["error_pct"]) for row in common) / len(common)
    aforo_mape = sum(abs(row["aforo_error_pct"]) for row in common) / len(common)
    assert round(mape, 1) == summary["ridge"]["mape_pct"]
    assert round(aforo_mape, 1) == summary["aforo"]["mape_pct"]


def test_campaign_errors_sign_and_closer(client: TestClient) -> None:
    rows = client.get("/models/errors").json()
    assert rows, "the fixture has at least one comparable row"
    row = rows[0]
    expected = 100 * (row["pred_t"] - row["oil_final_t"]) / row["oil_final_t"]
    assert row["error_pct"] == pytest.approx(expected, abs=0.01)
    if row["like_for_like"]:
        assert row["closer"] in {"oliveye", "aforo", "tie"}


def test_reference_price_from_published_data() -> None:
    data = Path(__file__).resolve().parents[1] / "api" / "data"
    price = TestClient(create_app(data)).get("/prices/reference").json()
    assert price["low_eur_per_kg"] == min(price["eur_per_kg"].values())
    assert price["high_eur_per_kg"] == max(price["eur_per_kg"].values())
    assert price["source_url"].startswith("https://")


def test_reference_price_missing_is_404(client: TestClient) -> None:
    assert client.get("/prices/reference").status_code == 404
