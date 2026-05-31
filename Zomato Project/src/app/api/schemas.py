"""Request and response models for the recommendation API."""

from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.config import get_max_additional_preferences_length, get_max_top_k

BudgetLiteral = Literal["low", "medium", "high"]


class RecommendationRequest(BaseModel):
    location: str = Field(..., min_length=1, max_length=100)
    budget: BudgetLiteral
    cuisine: str = Field(..., min_length=1, max_length=100)
    min_rating: float = Field(..., ge=0.0, le=5.0)
    additional_preferences: Optional[str] = Field(default=None)
    recommendation_count: int = Field(default=5, ge=1)

    @field_validator("location", "cuisine")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("additional_preferences")
    @classmethod
    def validate_additional_length(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        max_len = get_max_additional_preferences_length()
        if len(stripped) > max_len:
            raise ValueError(f"additional_preferences must be at most {max_len} characters")
        return stripped

    @field_validator("recommendation_count")
    @classmethod
    def validate_recommendation_count_cap(cls, value: int) -> int:
        cap = get_max_top_k()
        if value > cap:
            raise ValueError(f"recommendation_count must be at most {cap}")
        return value


class RecommendationItem(BaseModel):
    restaurant_id: str
    name: str
    cuisine: str
    rating: Optional[float] = None
    estimated_cost: Optional[Union[float, str]] = None
    location: str
    explanation: str


class RecommendationMetadata(BaseModel):
    candidates_considered: int
    model: str = "stub"
    latency_ms: int


class RecommendationResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    metadata: RecommendationMetadata
    summary: Optional[str] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "missing", "empty"]
    row_count: Optional[int] = None


class LocationEntry(BaseModel):
    city: str
    locality: str


class LocationsResponse(BaseModel):
    locations: List[LocationEntry]
    total: int

