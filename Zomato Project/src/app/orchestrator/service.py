"""Recommendation orchestrator: coordinate preference filter, LLM ranking, and validation/merge."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.api.stub import build_stub_explanation
from app.config import get_llm_model, get_max_candidates, is_llm_enabled
from app.filter import PreferenceFilter, UserPreferences
from app.llm.engine import RecommendationLLMEngine

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    """Consolidated recommendation result from the orchestrator."""

    items: List[Dict[str, Any]]
    summary: Optional[str]
    message: Optional[str]
    candidates_considered: int
    model_name: str
    degraded: bool
    latency_ms: int
    correlation_id: str
    timings_ms: Dict[str, int]
    dropped_invalid_ids: int


class RecommendationOrchestrator:
    """
    Orchestrate recommendation generation.
    
    Stages: Preference Normalization -> Candidates Filtering -> Truncation/Cap -> LLM Prompt -> LLM Execution -> Validation & Merging
    """

    def __init__(
        self,
        preference_filter: Optional[PreferenceFilter] = None,
        llm_engine: Optional[RecommendationLLMEngine] = None,
        *,
        use_llm: Optional[bool] = None,
    ) -> None:
        self._filter = preference_filter or PreferenceFilter()
        self._llm_engine = llm_engine or RecommendationLLMEngine()
        self._use_llm = use_llm if use_llm is not None else is_llm_enabled()

    def recommend(
        self,
        *,
        location: str,
        budget: str,
        cuisine: str,
        min_rating: float,
        additional_preferences: Optional[str],
        top_k: int,
    ) -> OrchestratorResult:
        correlation_id = uuid.uuid4().hex[:8]
        started = time.perf_counter()

        logger.info(
            "[%s] Recommendation Orchestrator started: location=%r, budget=%r, cuisine=%r, min_rating=%r, top_k=%d",
            correlation_id,
            location,
            budget,
            cuisine,
            min_rating,
            top_k,
        )

        # 1. Normalize preferences
        normalized_location = location.strip()
        normalized_cuisine = cuisine.strip()
        normalized_additional_prefs = (
            additional_preferences.strip() if additional_preferences else None
        )

        # 2. Ask data layer / filter for candidates
        filter_started = time.perf_counter()
        prefs = UserPreferences(
            location=normalized_location,
            budget=budget,  # already validated/literal
            cuisine=normalized_cuisine,
            min_rating=min_rating,
            additional_preferences=normalized_additional_prefs,
            max_candidates=get_max_candidates(),
        )
        filter_result = self._filter.find_candidates(prefs)
        filter_latency = int((time.perf_counter() - filter_started) * 1000)

        logger.info(
            "[%s] Stage: preference filter completed. Matched candidates: %d, Truncated: %s, Latency: %d ms",
            correlation_id,
            filter_result.total_matched,
            filter_result.truncated,
            filter_latency,
        )

        # 3. If zero candidates, return early with helpful message
        if filter_result.is_empty:
            total_latency = int((time.perf_counter() - started) * 1000)
            logger.info(
                "[%s] Orchestrator completed recommendation early (zero candidates). Total Latency: %d ms",
                correlation_id,
                total_latency,
            )
            return OrchestratorResult(
                items=[],
                summary=None,
                message=filter_result.message,
                candidates_considered=filter_result.total_matched,
                model_name="none",
                degraded=False,
                latency_ms=total_latency,
                correlation_id=correlation_id,
                timings_ms={"filter": filter_latency},
                dropped_invalid_ids=0,
            )

        # 4. Cap/pre-truncate candidates (handled inside find_candidates already capped at max_candidates)
        candidates = filter_result.candidates

        model_name = "stub"
        summary: Optional[str] = None
        degraded = False
        dropped_invalid_ids = 0
        llm_latency = 0

        # 5. Build prompt, call LLM and validate/merge
        if self._use_llm:
            llm_started = time.perf_counter()
            try:
                logger.info(
                    "[%s] Stage: calling LLM engine with %d candidates",
                    correlation_id,
                    len(candidates),
                )
                merged = self._llm_engine.rank_and_explain(
                    location=normalized_location,
                    budget=budget,
                    cuisine=normalized_cuisine,
                    min_rating=min_rating,
                    additional_preferences=normalized_additional_prefs,
                    candidates=candidates,
                    top_k=top_k,
                )
                llm_latency = int((time.perf_counter() - llm_started) * 1000)
                model_name = get_llm_model()
                summary = merged.summary
                degraded = merged.parse_failed
                dropped_invalid_ids = merged.dropped_invalid_ids
                rows = merged.items

                logger.info(
                    "[%s] Stage: LLM complete. Model: %s, Degraded: %s, Dropped IDs: %d, Latency: %d ms",
                    correlation_id,
                    model_name,
                    degraded,
                    dropped_invalid_ids,
                    llm_latency,
                )
            except Exception as exc:
                llm_latency = int((time.perf_counter() - llm_started) * 1000)
                logger.exception(
                    "[%s] LLM recommendation failed, using stub fallback: %s",
                    correlation_id,
                    exc,
                )
                degraded = True
                rows = self._stub_rows(
                    candidates[:top_k],
                    normalized_cuisine,
                    budget,
                    min_rating,
                    normalized_location,
                )
        else:
            rows = self._stub_rows(
                candidates[:top_k],
                normalized_cuisine,
                budget,
                min_rating,
                normalized_location,
            )

        total_latency = int((time.perf_counter() - started) * 1000)

        # Final deduplication safety net — remove any duplicate restaurants that
        # slipped through filter or LLM merge stages
        rows = self._deduplicate_items(rows)

        logger.info(
            "[%s] Recommendation Orchestrator completed recommendation. Items: %d, Total Latency: %d ms",
            correlation_id,
            len(rows),
            total_latency,
        )

        return OrchestratorResult(
            items=rows,
            summary=summary,
            message=None,
            candidates_considered=filter_result.total_matched,
            model_name=model_name,
            degraded=degraded,
            latency_ms=total_latency,
            correlation_id=correlation_id,
            timings_ms={"filter": filter_latency, "llm": llm_latency},
            dropped_invalid_ids=dropped_invalid_ids,
        )

    @staticmethod
    def _deduplicate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate restaurants from the final recommendation list.

        Uses normalized (name, city) as the identity key. Keeps
        the first occurrence (highest-ranked). This is a defense-in-depth
        measure on top of the filter-level dedup.
        """
        seen: set = set()
        unique: List[Dict[str, Any]] = []
        for item in items:
            name = (item.get("name") or "").strip().lower()
            city = (item.get("city") or "").strip().lower()
            key = (name, city)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _stub_rows(
        self,
        candidates: List[dict],
        cuisine_query: str,
        budget: str,
        min_rating: float,
        location_query: str,
    ) -> List[dict]:
        rows = []
        for c in candidates:
            row = dict(c)
            row["explanation"] = build_stub_explanation(
                c,
                cuisine_query=cuisine_query,
                budget=budget,
                min_rating=min_rating,
                location_query=location_query,
            )
            rows.append(row)
        return rows

