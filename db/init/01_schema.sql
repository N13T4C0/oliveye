-- OlivEye tables. Idempotent: run by the PostGIS container on first start, and again by
-- `scripts/load_postgis.py` (oliveye.db.load.apply_schema) on databases created earlier.
--
-- CRS discipline: geometries are stored in EPSG:4326 (WGS 84, what web maps and GeoJSON use);
-- areas are computed in EPSG:25830 (ETRS89 / UTM 30N, metres), never in degrees.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS oliveye;

-- Municipalities of Jaén (23) and Granada (18) with SIGPAC olive area.
CREATE TABLE IF NOT EXISTS oliveye.municipality (
    province_code      text    NOT NULL,
    municipality_code  text    NOT NULL,
    name               text    NOT NULL,
    olive_ha_sigpac    double precision NOT NULL CHECK (olive_ha_sigpac >= 0),
    processed          boolean NOT NULL,
    PRIMARY KEY (province_code, municipality_code)
);
COMMENT ON TABLE oliveye.municipality IS
    'Municipalities with SIGPAC olive hectares; processed = has Sentinel-2 series.';

-- Olive area actually measured: 250 m cells with at least 80 percent olive grove, dissolved per municipality.
CREATE TABLE IF NOT EXISTS oliveye.olive_area (
    province_code      text    NOT NULL,
    municipality_code  text    NOT NULL,
    olive_ha           double precision NOT NULL,
    cells              integer NOT NULL CHECK (cells > 0),
    geom               geometry(MultiPolygon, 4326) NOT NULL,
    PRIMARY KEY (province_code, municipality_code),
    FOREIGN KEY (province_code, municipality_code)
        REFERENCES oliveye.municipality (province_code, municipality_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS olive_area_geom_idx ON oliveye.olive_area USING gist (geom);
COMMENT ON TABLE oliveye.olive_area IS 'Measured olive area (EPSG:4326) per municipality.';

-- Monthly NDVI / NDMI per municipality (olive-area-weighted mean of the cells, outliers removed).
CREATE TABLE IF NOT EXISTS oliveye.monthly_index (
    province_code      text    NOT NULL,
    municipality_code  text    NOT NULL,
    month              date    NOT NULL CHECK (extract(day FROM month) = 1),
    ndvi               double precision CHECK (ndvi BETWEEN -1 AND 1),
    ndmi               double precision CHECK (ndmi BETWEEN -1 AND 1),
    valid_cells        integer,
    PRIMARY KEY (province_code, municipality_code, month),
    FOREIGN KEY (province_code, municipality_code)
        REFERENCES oliveye.municipality (province_code, municipality_code) ON DELETE CASCADE
);
COMMENT ON COLUMN oliveye.monthly_index.month IS 'First day of the month (monthly median composite).';

-- Olive oil per province and campaign: final figure, official aforo and OlivEye (LOCO) estimate.
CREATE TABLE IF NOT EXISTS oliveye.production (
    province       text NOT NULL,  -- name as published by the Junta ("Jaén", "Granada")
    province_code  text NOT NULL CHECK (province_code IN ('18', '23')),  -- INE code, joins municipality
    campaign       text NOT NULL CHECK (campaign ~ '^\d{4}/\d{2}$'),
    oil_final_t    double precision,
    oil_aforo_t    double precision,
    pred_t         double precision,
    target_method  text,
    PRIMARY KEY (province, campaign)
);
COMMENT ON COLUMN oliveye.production.pred_t IS
    'OlivEye estimate made leave-one-campaign-out (never saw that campaign nor the next).';

-- Measured area recomputed in metres, next to the value the pipeline reported.
-- Views hold no data: drop and recreate so a changed column list never blocks a load.
DROP VIEW IF EXISTS oliveye.v_olive_area_check;
CREATE VIEW oliveye.v_olive_area_check AS
SELECT
    m.province_code,
    m.municipality_code,
    m.name,
    m.olive_ha_sigpac,
    a.olive_ha,
    ST_Area(ST_Transform(a.geom, 25830)) / 1e4 AS footprint_ha,
    round((100 * a.olive_ha / NULLIF(m.olive_ha_sigpac, 0))::numeric, 1) AS measured_pct
FROM oliveye.municipality AS m
JOIN oliveye.olive_area AS a USING (province_code, municipality_code);

-- Signed percentage error of OlivEye and the aforo per campaign (same definition as GET /models/errors).
DROP VIEW IF EXISTS oliveye.v_campaign_error;
CREATE VIEW oliveye.v_campaign_error AS
SELECT
    province,
    campaign,
    oil_final_t,
    pred_t,
    oil_aforo_t,
    100 * (pred_t - oil_final_t) / oil_final_t AS error_pct,
    100 * (oil_aforo_t - oil_final_t) / oil_final_t AS aforo_error_pct,
    CASE
        WHEN oil_aforo_t IS NULL THEN NULL
        WHEN abs(pred_t - oil_final_t) < abs(oil_aforo_t - oil_final_t) THEN 'oliveye'
        WHEN abs(pred_t - oil_final_t) > abs(oil_aforo_t - oil_final_t) THEN 'aforo'
        ELSE 'tie'
    END AS closer,
    oil_aforo_t IS NOT NULL AS like_for_like,
    target_method  -- 'derived_from_aforo': back-calculated from the Junta's published variations
FROM oliveye.production
WHERE pred_t IS NOT NULL AND oil_final_t > 0;
