"""Reference olive oil prices for the web's "value of the harvest" figure.

The harvest is sold in several qualities (virgen extra, virgen, lampante) whose mix is unknown in
advance, so the web shows a **range**: tonnes x the lowest and highest category price of one
dated Poolred week. The page always states that week and the source.

Example: Jaén aforo 575,000 t x 2.88-3.16 EUR/kg = about 1,660-1,820 million euros.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

CATEGORIES = ("virgen_extra", "virgen", "lampante")
# Olive oil weighs about 0.916 kg per litre at 20 °C, so one tonne is about 1,092 litres.
OIL_DENSITY_KG_PER_L = 0.916


def price_payload(csv_path: Path) -> dict[str, Any]:
    """The latest week in `oil_prices.csv` as the JSON served at GET /prices/reference."""
    table = pd.read_csv(csv_path, dtype={"week_start": str, "week_end": str})
    unknown = set(table["category"]) - set(CATEGORIES)
    if unknown:
        raise ValueError(f"Unknown oil categories: {sorted(unknown)}")
    latest = table[table["week_end"] == table["week_end"].max()]
    prices = {row.category: float(row.eur_per_kg) for row in latest.itertuples()}
    first = latest.iloc[0]
    return {
        "week_start": first["week_start"],
        "week_end": first["week_end"],
        "eur_per_kg": prices,
        "low_eur_per_kg": min(prices.values()),
        "high_eur_per_kg": max(prices.values()),
        "source": first["source"],
        "source_url": first["source_url"],
        "oil_density_kg_per_l": OIL_DENSITY_KG_PER_L,
    }
