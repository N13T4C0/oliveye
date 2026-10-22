-- Runs once when the PostGIS container is first created.
-- Enables spatial types/functions and keeps project tables in their own schema.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS oliveye;
COMMENT ON SCHEMA oliveye IS 'OlivEye project tables (parcels, indices, climate, production).';
