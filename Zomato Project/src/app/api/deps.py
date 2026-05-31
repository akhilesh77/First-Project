"""FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import Header, HTTPException, status

from app.api.service import RecommendationService
from app.config import get_api_key, get_database_path
from app.data.repository import RestaurantRepository


@lru_cache
def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


def verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> None:
    expected = get_api_key()
    if expected is None:
        return
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def check_database_ready() -> int:
    """Return row count if DB is usable; raise HTTPException otherwise."""
    try:
        db_path = get_database_path()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database configuration error: {exc}",
        )
    if not db_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restaurant database is not available. Run ingestion first.",
        )
    try:
        stats = RestaurantRepository(db_path).get_stats()
        count = int(stats.get("row_count") or 0)
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Restaurant database is empty. Run ingestion first.",
            )
        return count
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database access or query error: {exc}",
        )
