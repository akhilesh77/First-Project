"""Recommendation API service layer delegating to recommendation orchestrator."""

from __future__ import annotations

import logging
from typing import List, Optional

from app.api.schemas import (
    RecommendationItem,
    RecommendationMetadata,
    RecommendationRequest,
    RecommendationResponse,
)
from app.api.stub import (
    format_display_location,
    format_estimated_cost,
)
from app.filter import PreferenceFilter
from app.llm.engine import RecommendationLLMEngine
from app.orchestrator import RecommendationOrchestrator

logger = logging.getLogger(__name__)


class RecommendationService:
    """API service boundary that wraps and calls the core RecommendationOrchestrator."""

    def __init__(
        self,
        preference_filter: Optional[PreferenceFilter] = None,
        llm_engine: Optional[RecommendationLLMEngine] = None,
        *,
        use_llm: Optional[bool] = None,
    ) -> None:
        self._orchestrator = RecommendationOrchestrator(
            preference_filter=preference_filter,
            llm_engine=llm_engine,
            use_llm=use_llm,
        )

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        res = self._orchestrator.recommend(
            location=request.location,
            budget=request.budget,
            cuisine=request.cuisine,
            min_rating=request.min_rating,
            additional_preferences=request.additional_preferences,
            top_k=request.recommendation_count,
        )

        recommendations = [self._row_to_item(row) for row in res.items]

        return RecommendationResponse(
            recommendations=recommendations,
            summary=res.summary,
            message=res.message,
            metadata=RecommendationMetadata(
                candidates_considered=res.candidates_considered,
                model=res.model_name,
                latency_ms=res.latency_ms,
            ),
        )

    @staticmethod
    def _row_to_item(row: dict) -> RecommendationItem:
        return RecommendationItem(
            restaurant_id=row["restaurant_id"],
            name=row["name"],
            cuisine=row.get("cuisines") or "",
            rating=row.get("aggregate_rating"),
            estimated_cost=format_estimated_cost(
                row.get("cost_for_two"), row.get("budget_band")
            ),
            location=format_display_location(row.get("city"), row.get("neighborhood")),
            explanation=row.get("explanation") or "",
        )

