# data/

Local data only. Everything here is git-ignored except this file and the `.gitkeep` placeholders.

| Folder | Content | Rule |
|---|---|---|
| `raw/` | Original downloads exactly as received (SIGPAC shapefiles, production CSVs, climate). | Read-only. Never edit by hand. |
| `raw/sigpac/` | SIGPAC parcels for Jaén (23) and Granada (18). | Keep the original archive names. |
| `interim/` | Cleaned/filtered intermediate files (e.g. olive-only parcels as GeoParquet). | Reproducible from `raw/` with code. |
| `processed/` | Final feature tables ready for modelling. | Reproducible from `interim/`. |
| `cache/openeo/` | Results downloaded from openEO + `credits_log.csv`. | **Check here before any openEO request.** |
