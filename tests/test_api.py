"""Tests for the read-only API over exported results."""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from oliveye.api.app import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    pd.DataFrame(
        {
            "province_code": ["23", "23", "18"],
            "municipality_code": ["60", "92", "104"],
            "name": ["MARTOS", "UBEDA", "LOJA"],
            "olive_hectares": [21796.4, 30559.9, 9000.0],
            "processed": [True, False, True],
        }
    ).to_csv(tmp_path / "municipalities.csv", index=False)
    pd.DataFrame(
        {
            "province_code": ["23", "23"],
            "municipality_code": ["60", "60"],
            "month": ["2025-07", "2025-08"],
            "ndvi": [0.271, 0.260],
            "ndmi": [-0.068, -0.061],
            "valid_cells": [3130, 3130],
        }
    ).to_csv(tmp_path / "indices_monthly.csv", index=False)
    pd.DataFrame(
        {
            "province": ["Jaén", "Jaén"],
            "campaign": ["2024/25", "2025/26"],
            "oil_final_t": [560800.0, 389000.0],
            "oil_aforo_t": [445000.0, 475000.0],
            "pred_t": [500000.0, 410000.0],
        }
    ).to_csv(tmp_path / "production.csv", index=False)
    pd.DataFrame(
        {
            "model": ["aforo", "ridge"],
            "rows": [15, 16],
            "mape_pct": [11.9, 20.0],
            "wins_vs_aforo": [0, 5],
        }
    ).to_csv(tmp_path / "summary.csv", index=False)
    return TestClient(create_app(tmp_path))


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_municipalities_filtered_by_province(client: TestClient) -> None:
    response = client.get("/municipalities", params={"province": "23"})

    assert response.status_code == 200
    names = [m["name"] for m in response.json()]
    assert names == ["MARTOS", "UBEDA"]


def test_monthly_indices_of_a_municipality(client: TestClient) -> None:
    response = client.get("/municipalities/23/60/indices")

    body = response.json()
    assert [row["month"] for row in body] == ["2025-07", "2025-08"]
    assert body[0]["ndvi"] == pytest.approx(0.271)


def test_unknown_municipality_is_404(client: TestClient) -> None:
    assert client.get("/municipalities/23/999/indices").status_code == 404


def test_province_production_series(client: TestClient) -> None:
    body = client.get("/provinces/Jaén/production").json()

    assert body[0] == {
        "campaign": "2024/25",
        "oil_final_t": 560800.0,
        "oil_aforo_t": 445000.0,
        "pred_t": 500000.0,
    }


def test_model_summary(client: TestClient) -> None:
    body = client.get("/models/summary").json()
    assert {m["model"] for m in body} == {"aforo", "ridge"}
