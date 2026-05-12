from typing import Any, Dict, List, Optional

from psycopg.sql import SQL


def _round_distance(value: Any) -> float:
    # Normalize distance values to two decimal places.
    return round(float(value), 2)


def fetch_places(connection, category: Optional[str] = None) -> List[Dict[str, Any]]:
    # Load all places, optionally filtered by category.
    query = """
        SELECT id, name, category, address, latitude, longitude
        FROM places
        WHERE (%(category)s::text IS NULL OR category = %(category)s::text)
        ORDER BY category, name;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, {"category": category})
        return cursor.fetchall()


def fetch_categories(connection) -> List[str]:
    # Fetch distinct place categories for UI filters.
    query = """
        SELECT DISTINCT category
        FROM places
        ORDER BY category;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
    return [row["category"] for row in rows]


def nearest_places(connection, lat: float, lon: float, k: int = 5, category: Optional[str] = None,) -> List[Dict[str, Any]]:
    # Return k nearest places to the given point using ST_Distance.
    query = """
        SELECT id, name, category, address, latitude, longitude,
            ROUND(
                CAST(
                    ST_Distance(
                        geom,
                        ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
                    ) AS numeric
                ),
                2
            ) AS distance_m
        FROM places
        WHERE (%(category)s::text IS NULL OR category = %(category)s::text)
        ORDER BY ST_Distance(
            geom,
            ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
        )
        LIMIT %(k)s;
    """
    params = {"lat": lat, "lon": lon, "k": k, "category": category}
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    for row in rows:
        row["distance_m"] = _round_distance(row["distance_m"])
    return rows


def radius_places(
    connection,
    lat: float,
    lon: float,
    radius_m: float,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # Return places within radius_m meters using ST_DWithin.
    query = """
        SELECT id, name, category, address, latitude, longitude,
            ROUND(
                CAST(
                    ST_Distance(
                        geom,
                        ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
                    ) AS numeric
                ),
                2
            ) AS distance_m
        FROM places
        WHERE ST_DWithin(
            geom,
            ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
            %(radius_m)s
        )
        AND (%(category)s::text IS NULL OR category = %(category)s::text)
        ORDER BY distance_m, name;
    """
    params = {"lat": lat, "lon": lon, "radius_m": radius_m, "category": category}
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    for row in rows:
        row["distance_m"] = _round_distance(row["distance_m"])
    return rows


def polygon_places(
    connection,
    coordinates: List[List[float]],
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # Return places intersecting the input polygon (WKT built from coordinates).
    closed_coordinates = list(coordinates)
    if closed_coordinates[0] != closed_coordinates[-1]:
        closed_coordinates.append(closed_coordinates[0])

    polygon_text = ",".join(f"{lon} {lat}" for lon, lat in closed_coordinates)
    wkt_polygon = f"POLYGON(({polygon_text}))"

    query = """
        SELECT id, name, category, address, latitude, longitude
        FROM places
        WHERE ST_Intersects(
            geom::geometry,
            ST_GeomFromText(%(polygon)s, 4326)
        )
        AND (%(category)s::text IS NULL OR category = %(category)s::text)
        ORDER BY category, name;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, {"polygon": wkt_polygon, "category": category})
        return cursor.fetchall()


def explain_radius(connection, lat: float, lon: float, radius_m: float, category: Optional[str]) -> List[str]:
    # Execute EXPLAIN ANALYZE for the radius query and return the plan lines.
    query = """
        SELECT id
        FROM places
        WHERE ST_DWithin(
            geom,
            ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
            %(radius_m)s
        )
        AND (%(category)s::text IS NULL OR category = %(category)s::text)
    """
    params = {"lat": lat, "lon": lon, "radius_m": radius_m, "category": category}
    explain_query = SQL("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {}").format(SQL(query))
    with connection.cursor() as cursor:
        cursor.execute(explain_query, params)
        rows = cursor.fetchall()
    return [row["QUERY PLAN"] for row in rows]
