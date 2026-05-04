CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS places (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    address TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOGRAPHY(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_places_geom_gist
    ON places
    USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_places_category
    ON places (category);
