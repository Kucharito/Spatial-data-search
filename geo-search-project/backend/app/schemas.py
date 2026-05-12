from typing import List, Optional

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class ProjectInfoResponse(BaseModel):
    project: str
    topic: str
    stack: List[str]


class HealthResponse(BaseModel):
    status: str
    database: str


class ImportResponse(BaseModel):
    imported_count: int
    cleared_before_import: bool
    source_file: str


class CategoryListResponse(BaseModel):
    categories: List[str]


class PlaceBase(BaseModel):
    id: int
    name: str
    category: str
    address: Optional[str] = None
    latitude: float
    longitude: float


class PlaceResponse(PlaceBase):
    pass


class NearbyPlaceResponse(PlaceBase):
    distance_m: float


class ExplainResponse(BaseModel):
    query_type: str
    plan: List[str]


class PolygonSearchRequest(BaseModel):
    coordinates: List[List[float]] = Field(..., min_length=3)
    category: Optional[str] = None
