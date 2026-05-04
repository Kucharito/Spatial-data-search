CREATE INDEX IF NOT EXISTS idx_places_geom_gist
    ON places
    USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_places_category
    ON places (category);
