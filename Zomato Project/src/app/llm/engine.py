"""Orchestrate Grok prompt → completion → merge."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.llm.client import GrokClient, GrokClientError
from app.llm.prompts import build_messages, preferences_from_request
from app.validation.merger import MergeResult, _fallback_merge, merge_llm_rankings

logger = logging.getLogger(__name__)


class RecommendationLLMEngine:
    """Rank and explain candidates using xAI Grok."""

    def __init__(self, client: Optional[GrokClient] = None) -> None:
        self._client = client

    def _get_client(self) -> GrokClient:
        if self._client is None:
            self._client = GrokClient()
        return self._client

    def rank_and_explain(
        self,
        *,
        location: str,
        budget: str,
        cuisine: str,
        min_rating: float,
        additional_preferences: Optional[str],
        candidates: List[Dict[str, Any]],
        top_k: int,
    ) -> MergeResult:
        if not candidates:
            return MergeResult(items=[], summary=None)

        prefs = preferences_from_request(
            location=location,
            budget=budget,
            cuisine=cuisine,
            min_rating=min_rating,
            additional_preferences=additional_preferences,
        )
        messages = build_messages(
            preferences=prefs,
            candidates=candidates,
            top_k=top_k,
        )

        try:
            raw = self._get_client().chat_completion(messages)
        except GrokClientError as exc:
            logger.error("Grok call failed: %s", exc)
            return _fallback_merge(
                candidates,
                top_k=top_k,
                cuisine_query=cuisine,
                budget=budget,
                min_rating=min_rating,
                location_query=location,
                parse_failed=True,
            )

        return merge_llm_rankings(
            raw,
            candidates,
            top_k=top_k,
            cuisine_query=cuisine,
            budget=budget,
            min_rating=min_rating,
            location_query=location,
        )
