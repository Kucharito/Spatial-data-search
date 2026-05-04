-- 1. Vsetky miesta
SELECT id, name, category, address, latitude, longitude
FROM places
ORDER BY category, name;

-- 2. Najblizsich 5 miest k zadanemu bodu
SELECT
    id,
    name,
    category,
    ROUND(
        CAST(
            ST_Distance(
                geom,
                ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography
            ) AS numeric
        ),
        2
    ) AS distance_m
FROM places
ORDER BY ST_Distance(
    geom,
    ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography
)
LIMIT 5;

-- 3. Miesta v okruhu 1000 m
SELECT
    id,
    name,
    category,
    ROUND(
        CAST(
            ST_Distance(
                geom,
                ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography
            ) AS numeric
        ),
        2
    ) AS distance_m
FROM places
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography,
    1000
)
ORDER BY distance_m;

-- 4. Miesta vo vnutri polygonu
SELECT id, name, category, address
FROM places
WHERE ST_Intersects(
    geom::geometry,
    ST_GeomFromText(
        'POLYGON((18.2390 49.8360,18.2860 49.8360,18.2860 49.8070,18.2390 49.8070,18.2390 49.8360))',
        4326
    )
);

-- 5. EXPLAIN ANALYZE pre radius query
EXPLAIN ANALYZE
SELECT id, name
FROM places
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography,
    1000
);

-- 6. Vytvorenie priestoroveho indexu
CREATE INDEX IF NOT EXISTS idx_places_geom_gist
    ON places
    USING GIST (geom);

-- 7. Zmazanie priestoroveho indexu
DROP INDEX IF EXISTS idx_places_geom_gist;
