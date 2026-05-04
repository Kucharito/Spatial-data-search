from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .database import get_connection
from .importer import import_places
from .schemas import (
    BenchmarkResponse,
    CategoryListResponse,
    ExplainResponse,
    HealthResponse,
    ImportResponse,
    NearbyPlaceResponse,
    PlaceResponse,
    PolygonSearchRequest,
    ProjectInfoResponse,
)
from .spatial_queries import (
    benchmark_query,
    explain_radius,
    fetch_categories,
    fetch_places,
    nearest_benchmark_payload,
    nearest_places,
    polygon_places,
    radius_benchmark_payload,
    radius_places,
)

app = FastAPI(
    title="Geo Search Project API",
    description="Spatial database object finder using PostgreSQL, PostGIS and FastAPI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=ProjectInfoResponse)
def root() -> ProjectInfoResponse:
    return ProjectInfoResponse(
        project="Geo Search Project – Spatial Database Object Finder",
        topic="Storage and querying of spatial data in a database system",
        stack=[
            "PostgreSQL",
            "PostGIS",
            "Docker Compose",
            "Python",
            "FastAPI",
            "psycopg",
            "Leaflet",
        ],
    )


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Version() AS version;")
            result = cursor.fetchone()
        return HealthResponse(status="ok", database=f"connected (PostGIS {result['version']})")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}") from exc


@app.post("/import", response_model=ImportResponse)
def import_data(clear: bool = True) -> ImportResponse:
    try:
        with get_connection() as connection:
            imported_count, source_path = import_places(connection, clear=clear)
        return ImportResponse(
            imported_count=imported_count,
            cleared_before_import=clear,
            source_file=str(source_path),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc


@app.get("/places", response_model=List[PlaceResponse])
def get_places(category: Optional[str] = None) -> List[PlaceResponse]:
    try:
        with get_connection() as connection:
            rows = fetch_places(connection, category=category)
        return [PlaceResponse(**row) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load places: {exc}") from exc


@app.get("/categories", response_model=CategoryListResponse)
def get_categories() -> CategoryListResponse:
    try:
        with get_connection() as connection:
            categories = fetch_categories(connection)
        return CategoryListResponse(categories=categories)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load categories: {exc}") from exc


@app.get("/places/nearest", response_model=List[NearbyPlaceResponse])
def get_nearest_places(
    lat: float,
    lon: float,
    k: int = Query(5, ge=1, le=50),
    category: Optional[str] = None,
) -> List[NearbyPlaceResponse]:
    try:
        with get_connection() as connection:
            rows = nearest_places(connection, lat=lat, lon=lon, k=k, category=category)
        return [NearbyPlaceResponse(**row) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Nearest search failed: {exc}") from exc


@app.get("/places/radius", response_model=List[NearbyPlaceResponse])
def get_places_in_radius(
    lat: float,
    lon: float,
    radius_m: float = Query(..., gt=0),
    category: Optional[str] = None,
) -> List[NearbyPlaceResponse]:
    try:
        with get_connection() as connection:
            rows = radius_places(connection, lat=lat, lon=lon, radius_m=radius_m, category=category)
        return [NearbyPlaceResponse(**row) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Radius search failed: {exc}") from exc


@app.post("/places/in-polygon", response_model=List[PlaceResponse])
def get_places_in_polygon(request: PolygonSearchRequest) -> List[PlaceResponse]:
    try:
        if len(request.coordinates) < 3:
            raise HTTPException(status_code=400, detail="Polygon must contain at least 3 coordinates.")

        with get_connection() as connection:
            rows = polygon_places(connection, coordinates=request.coordinates, category=request.category)
        return [PlaceResponse(**row) for row in rows]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Polygon search failed: {exc}") from exc


@app.get("/benchmark/nearest", response_model=BenchmarkResponse)
def benchmark_nearest(
    lat: float,
    lon: float,
    k: int = Query(5, ge=1, le=50),
    category: Optional[str] = None,
) -> BenchmarkResponse:
    try:
        query, params, note = nearest_benchmark_payload(lat=lat, lon=lon, k=k, category=category)
        with get_connection() as connection:
            payload = benchmark_query(connection, query=query, params=params, query_type="nearest", note=note)
        return BenchmarkResponse(**payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Nearest benchmark failed: {exc}") from exc


@app.get("/benchmark/radius", response_model=BenchmarkResponse)
def benchmark_radius(
    lat: float,
    lon: float,
    radius_m: float = Query(..., gt=0),
    category: Optional[str] = None,
) -> BenchmarkResponse:
    try:
        query, params, note = radius_benchmark_payload(
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            category=category,
        )
        with get_connection() as connection:
            payload = benchmark_query(connection, query=query, params=params, query_type="radius", note=note)
        return BenchmarkResponse(**payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Radius benchmark failed: {exc}") from exc


@app.get("/explain/radius", response_model=ExplainResponse)
def explain_radius_query(
    lat: float,
    lon: float,
    radius_m: float = Query(..., gt=0),
    category: Optional[str] = None,
) -> ExplainResponse:
    try:
        with get_connection() as connection:
            plan = explain_radius(connection, lat=lat, lon=lon, radius_m=radius_m, category=category)
        return ExplainResponse(query_type="radius", plan=plan)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"EXPLAIN failed: {exc}") from exc
