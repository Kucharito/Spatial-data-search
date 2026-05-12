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


-- 7. Vytvorenie priestoroveho GiST indexu
CREATE INDEX IF NOT EXISTS idx_places_geom_gist
    ON places
    USING GIST (geom);

-- 8. Zmazanie priestoroveho indexu pre porovnanie vykonu bez indexu
DROP INDEX IF EXISTS idx_places_geom_gist;




/*
cd "C:\Users\adamk\OneDrive\Počítač\Databazy Projekt\geo-search-project"
docker exec -it geo-search-db psql -U postgres -d geodb

DROP INDEX IF EXISTS idx_places_geom_gist;
ANALYZE places;

\timing on

BEGIN;

CREATE INDEX IF NOT EXISTS idx_places_geom_gist ON places USING GIST (geom);
ANALYZE places;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM places
WHERE ST_DWithin(
  geom,
  ST_SetSRID(ST_MakePoint(17.1077, 48.1486), 4326),
  0.01
);

ROLLBACK;


test s indexom

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM places
WHERE ST_DWithin(
  geom,
  ST_SetSRID(ST_MakePoint(17.1077, 48.1486), 4326),
  0.01
);

*/



/*
\timing on
ANALYZE places;

-- 1) S INDEXOM
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name
FROM places
WHERE ST_DWithin(
  geom,
  ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography,
  1000
);

-- 2) DROP INDEX
DROP INDEX IF EXISTS idx_places_geom_gist;
ANALYZE places;

-- 3) BEZ INDEXU
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name
FROM places
WHERE ST_DWithin(
  geom,
  ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography,
  1000
);

-- 4) VYTVOR INDEX NASPAT
CREATE INDEX IF NOT EXISTS idx_places_geom_gist ON places USING GIST (geom);
ANALYZE places;



*/

/*
-- TEST 3: NEAREST (ORDER BY ST_Distance) s/bez indexu
\timing on
ANALYZE places;

-- 1) S INDEXOM
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name
FROM places
ORDER BY ST_Distance(
    geom,
    ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography
)
LIMIT 10;

-- 2) DROP INDEX
DROP INDEX IF EXISTS idx_places_geom_gist;
ANALYZE places;

-- 3) BEZ INDEXU
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name
FROM places
ORDER BY ST_Distance(
    geom,
    ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography
)
LIMIT 10;

-- 4) VYTVOR INDEX NASPAT
CREATE INDEX IF NOT EXISTS idx_places_geom_gist ON places USING GIST (geom);
ANALYZE places;
*/

/*
-- TEST 4: RADIUS + CATEGORY FILTER (kombinacia GiST a B-tree)
\timing on
ANALYZE places;

-- 1) S INDEXAMI
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name
FROM places
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography,
    1500
)
AND category = 'restaurant';

-- 2) DROP INDEXY
DROP INDEX IF EXISTS idx_places_geom_gist;
DROP INDEX IF EXISTS idx_places_category;
ANALYZE places;

-- 3) BEZ INDEXOV
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name
FROM places
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326)::geography,
    1500
)
AND category = 'restaurant';

-- 4) VYTVOR INDEXY NASPAT
CREATE INDEX IF NOT EXISTS idx_places_geom_gist ON places USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_places_category ON places (category);
ANALYZE places;
*/
