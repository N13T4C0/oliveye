# Curated sources

Small hand-curated reference tables, each row with its source URL, for values that are not
available as machine-readable files. Generated data never lives here (see `data/README.md`).

| File | Content |
|---|---|
| `aforo_press_releases.csv` | Junta aforo per province for campaigns without an online PDF (2016/17–2020/21, partial). From 2021/22 on, the aforo comes from the PDFs (`aforo_table` job). |
| `oil_prices.csv` | Weekly olive oil origin price (€/kg) per category from Poolred, as reported by a farmers' association. Used only to give a dated, approximate value of the harvest on the web (range lampante–virgen extra). Update it by hand when refreshing the page. |
| `production_reported.csv` | Final production reported directly (AICA in Junta reports) or derived from a published provincial share. Takes precedence over values derived from aforo variations (ADR 0002). |
