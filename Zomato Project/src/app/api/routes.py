"""API route handlers."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import check_database_ready, get_recommendation_service, verify_api_key
from app.api.schemas import (
    ErrorResponse,
    HealthResponse,
    LocationsResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.api.service import RecommendationService
from app.config import get_database_path
from app.data.city import normalize_metro_city
from app.data.repository import RestaurantRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    try:
        db_path = get_database_path()
    except Exception:
        logger.exception("Database URL resolution failed in health check")
        return HealthResponse(status="degraded", database="missing", row_count=None)
        
    if not db_path.is_file():
        return HealthResponse(status="degraded", database="missing", row_count=None)
    try:
        stats = RestaurantRepository(db_path).get_stats()
        count = int(stats.get("row_count") or 0)
        if count == 0:
            return HealthResponse(status="degraded", database="empty", row_count=0)
        return HealthResponse(status="ok", database="ok", row_count=count)
    except Exception:
        logger.exception("Health check failed")
        return HealthResponse(status="degraded", database="missing", row_count=None)


@router.get(
    "/v1/locations",
    response_model=LocationsResponse,
    tags=["locations"],
)
def list_locations(
    city: Optional[str] = Query(default=None, max_length=100, description="Filter by metro city"),
) -> LocationsResponse:
    """Return deduplicated, sorted localities available in the dataset."""
    check_database_ready()
    normalized_city = normalize_metro_city(city) if city else None
    repo = RestaurantRepository(get_database_path())
    entries = repo.get_localities(city=normalized_city)
    return LocationsResponse(
        locations=entries,
        total=len(entries),
    )


@router.post(
    "/v1/recommendations",
    response_model=RecommendationResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    tags=["recommendations"],
    dependencies=[Depends(verify_api_key)],
)
def create_recommendations(
    body: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    check_database_ready()
    try:
        return service.recommend(body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Recommendation request failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating recommendations.",
        ) from exc

