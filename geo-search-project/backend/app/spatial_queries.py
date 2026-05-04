from typing import Any, Dict, List, Optional, Tuple

from psycopg.sql import SQL


def _round_distance(value: Any) -> float:
    return round(float(value), 2)


def fetch_places(connection, category: Optional[str] = None) -> List[Dict[str, Any]]:
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
    query = """
        SELECT DISTINCT category
        FROM places
        ORDER BY category;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
    return [row["category"] for row in rows]


def nearest_places(
    connection,
    lat: float,
    lon: float,
    k: int = 5,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = """
        SELECT
            id,
            name,
            category,
            address,
            latitude,
            longitude,
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
    query = """
        SELECT
            id,
            name,
            category,
            address,
            latitude,
            longitude,
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


def benchmark_query(connection, query: str, params: Dict[str, Any], query_type: str, note: str) -> Dict[str, Any]:
    explain_query = f"EXPLAIN (ANALYZE, FORMAT TEXT) {query}"
    with connection.cursor() as cursor:
        cursor.execute(explain_query, params)
        plan_rows = cursor.fetchall()

    execution_time_ms = 0.0
    for row in plan_rows:
        line = row["QUERY PLAN"]
        if line.startswith("Execution Time:"):
            execution_time_ms = float(line.split(":")[1].strip().split()[0])
            break

    count_query = f"SELECT COUNT(*) AS result_count FROM ({query}) AS subquery"
    with connection.cursor() as cursor:
        cursor.execute(count_query, params)
        result_count = cursor.fetchone()["result_count"]

    return {
        "result_count": result_count,
        "execution_time_ms": round(execution_time_ms, 3),
        "query_type": query_type,
        "note": note,
    }


def nearest_benchmark_payload(lat: float, lon: float, k: int, category: Optional[str]) -> Tuple[str, Dict[str, Any], str]:
    query = """
        SELECT id
        FROM places
        WHERE (%(category)s::text IS NULL OR category = %(category)s::text)
        ORDER BY ST_Distance(
            geom,
            ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
        )
        LIMIT %(k)s
    """
    note = (
        "Pri zapnutom GiST indexe na stlpci geom PostGIS zvycajne vie najst kandidaty rychlejsie; "
        "bez indexu databaza prechadza viac riadkov."
    )
    return query, {"lat": lat, "lon": lon, "k": k, "category": category}, note


def radius_benchmark_payload(lat: float, lon: float, radius_m: float, category: Optional[str]) -> Tuple[str, Dict[str, Any], str]:
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
    note = (
        "ST_DWithin je typicky operacia, pri ktorej sa priestorovy index prejavi najviac. "
        "Po odstraneni indexu bude plan castejsie smerovat k sekvencnemu scanu."
    )
    return query, {"lat": lat, "lon": lon, "radius_m": radius_m, "category": category}, note


def explain_radius(connection, lat: float, lon: float, radius_m: float, category: Optional[str]) -> List[str]:
    query, params, _ = radius_benchmark_payload(lat, lon, radius_m, category)
    explain_query = SQL("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {}").format(SQL(query))
    with connection.cursor() as cursor:
        cursor.execute(explain_query, params)
        rows = cursor.fetchall()
    return [row["QUERY PLAN"] for row in rows]
