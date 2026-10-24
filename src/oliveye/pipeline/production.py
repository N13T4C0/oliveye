"""Official harvest forecast (*aforo*) per province, parsed from the Junta de Andalucía PDFs.

Every September the Junta (CAPADR) publishes "Aforo de producción de olivar en Andalucía" for the
campaign that starts in October. Its table "Aforo de producción por provincias" gives, per
province: olives for oil mills (t), olive oil (t) and the oil variation versus the previous
campaign and versus the average of the last five campaigns.

The variation versus the previous campaign also lets us back out the **final production of the
previous campaign as the Junta measured it**: `previous = aforo / (1 + variation)`. That value is
derived (rounded inputs, ±0.5 % error) and is flagged as such; it is a cross-check for the AICA
series, not a replacement for it.

Campaign naming: "2024/25" = harvest from October 2024 to September 2025.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pdfplumber

PROVINCES: tuple[str, ...] = (
    "Almería",
    "Cádiz",
    "Córdoba",
    "Granada",
    "Huelva",
    "Jaén",
    "Málaga",
    "Sevilla",
    "Andalucía",
)
# INE province codes, to join with SIGPAC (`province_code`). Andalucía is the regional total.
PROVINCE_CODES: dict[str, str] = {
    "Almería": "04",
    "Cádiz": "11",
    "Córdoba": "14",
    "Granada": "18",
    "Huelva": "21",
    "Jaén": "23",
    "Málaga": "29",
    "Sevilla": "41",
    "Andalucía": "AN",
}

COLUMNS = [
    "campaign",
    "province",
    "province_code",
    "olives_aforo_t",
    "oil_aforo_t",
    "oil_var_prev_pct",
    "oil_var_5y_pct",
    "oil_prev_final_t_derived",
]


def parse_spanish_number(text: str) -> float:
    """'1.021.000' -> 1021000.0, '-43,5 %' -> -43.5 (dot = thousands, comma = decimals)."""
    cleaned = text.replace("%", "").replace(".", "").replace(",", ".").replace("−", "-")
    return float(cleaned.strip())


def normalise_campaign(text: str) -> str:
    """'2024_25', '2024-2025' or '2024/2025' -> '2024/25'."""
    match = re.search(r"(20\d{2})\D{1,2}(20)?(\d{2})", text)
    if match is None:
        raise ValueError(f"No campaign found in {text!r}")
    start, end = int(match.group(1)), int(match.group(3))
    if end != (start + 1) % 100:
        raise ValueError(f"Not consecutive years in {text!r}")
    return f"{start}/{end:02d}"


def _column(header: list[str], *keywords: str) -> int:
    """Index of the first header cell containing all keywords (case-insensitive)."""
    for i, cell in enumerate(header):
        flat = " ".join(cell.split()).lower()
        if all(k in flat for k in keywords):
            return i
    raise ValueError(f"No column with {keywords} in {header}")


def parse_province_table(rows: list[list[str | None]], campaign: str) -> pd.DataFrame:
    """Turn the raw 'Aforo de producción por provincias' table into tidy rows."""
    header = [cell or "" for cell in rows[0]]
    olives = _column(header, "aceituna")
    oil = _column(header, "aceite de oliva")
    var_prev = _column(header, "campaña anterior")
    var_5y = _column(header, "media")

    records = []
    for row in rows[1:]:
        cells = [cell or "" for cell in row]
        name = cells[0].strip().capitalize() if cells[0].isupper() else cells[0].strip()
        if name not in PROVINCES:
            continue
        oil_t = parse_spanish_number(cells[oil])
        prev_pct = parse_spanish_number(cells[var_prev])
        records.append(
            {
                "campaign": campaign,
                "province": name,
                "province_code": PROVINCE_CODES[name],
                "olives_aforo_t": parse_spanish_number(cells[olives]),
                "oil_aforo_t": oil_t,
                "oil_var_prev_pct": prev_pct,
                "oil_var_5y_pct": parse_spanish_number(cells[var_5y]),
                "oil_prev_final_t_derived": round(oil_t / (1 + prev_pct / 100), -2),
            }
        )
    if len(records) != len(PROVINCES):
        raise ValueError(f"Expected {len(PROVINCES)} rows, parsed {len(records)}")
    return pd.DataFrame(records, columns=COLUMNS)


def _is_province_table(rows: list[list[str | None]]) -> bool:
    header = " ".join(" ".join((cell or "").split()) for cell in rows[0]).lower()
    return "provincia" in header and "aforo aceite" in header and "campaña anterior" in header


def parse_aforo_pdf(path: Path, campaign: str | None = None) -> pd.DataFrame:
    """Find and parse the provincial aforo table in one Junta PDF.

    Args:
        path: the PDF file.
        campaign: e.g. "2024/25"; inferred from the file name when omitted.
    """
    campaign = campaign or normalise_campaign(path.stem)
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if table and _is_province_table(table):
                    return parse_province_table(table, campaign)
    raise ValueError(f"No provincial aforo table found in {path.name}")


def parse_aforo_pdfs(paths: list[Path]) -> pd.DataFrame:
    """Parse several PDFs into one table sorted by campaign and province."""
    frames = [parse_aforo_pdf(path) for path in paths]
    return pd.concat(frames).sort_values(["campaign", "province"]).reset_index(drop=True)


def previous_campaign(campaign: str) -> str:
    """'2024/25' -> '2023/24'."""
    start = int(normalise_campaign(campaign)[:4]) - 1
    return f"{start}/{(start + 1) % 100:02d}"


def final_production_series(*aforo_tables: pd.DataFrame) -> pd.DataFrame:
    """Final production per province and campaign, derived from the aforo variations (ADR 0002).

    Each input has `campaign`, `province`, `oil_aforo_t` and `oil_var_prev_pct` (the parsed PDF
    table, or the curated press-release table). The aforo of campaign t tells the final
    production of t-1. When several sources describe the same campaign, the first table wins.

    Returns:
        campaign, province, oil_final_t_derived, source_campaign (the aforo it came from).
    """
    frames = []
    for table in aforo_tables:
        usable = table.dropna(subset=["oil_aforo_t", "oil_var_prev_pct"])
        aforo = usable["oil_aforo_t"].astype(float)
        variation = usable["oil_var_prev_pct"].astype(float)
        frames.append(
            pd.DataFrame(
                {
                    "campaign": usable["campaign"].astype(str).map(previous_campaign),
                    "province": usable["province"],
                    "oil_final_t_derived": (aforo / (1 + variation / 100)).round(-2),
                    "source_campaign": usable["campaign"].astype(str),
                }
            )
        )
    series = pd.concat(frames, ignore_index=True)
    series = series.drop_duplicates(["campaign", "province"], keep="first")
    return series.sort_values(["province", "campaign"]).reset_index(drop=True)
