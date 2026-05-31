"""Tests for RecommendationOrchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.filter import FilterResult
from app.orchestrator.service import RecommendationOrchestrator
from app.validation.merger import MergeResult


def test_orchestrator_success():
    mock_filter = MagicMock()
    mock_filter.find_candidates.return_value = FilterResult(
        candidates=[{"restaurant_id": "r1", "name": "Test Restaurant", "city": "Bangalore"}],
        total_matched=1,
    )

    mock_engine = MagicMock()
    mock_engine.rank_and_explain.return_value = MergeResult(
        items=[
            {
                "restaurant_id": "r1",
                "name": "Test Restaurant",
                "city": "Bangalore",
                "explanation": "Perfect fit",
            }
        ],
        summary="Shortlist summary",
        parse_failed=False,
        dropped_invalid_ids=0,
    )

    orc = RecommendationOrchestrator(
        preference_filter=mock_filter,
        llm_engine=mock_engine,
        use_llm=True,
    )

    res = orc.recommend(
        location="Bangalore",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0,
        additional_preferences="quiet",
        top_k=3,
    )

    assert not res.degraded
    assert len(res.items) == 1
    assert res.items[0]["explanation"] == "Perfect fit"
    assert res.summary == "Shortlist summary"
    assert res.candidates_considered == 1
    assert res.correlation_id is not None
    assert "filter" in res.timings_ms
    assert "llm" in res.timings_ms


def test_orchestrator_zero_candidates():
    mock_filter = MagicMock()
    mock_filter.find_candidates.return_value = FilterResult(
        candidates=[],
        total_matched=0,
        message="No restaurants found",
    )

    mock_engine = MagicMock()
    orc = RecommendationOrchestrator(
        preference_filter=mock_filter,
        llm_engine=mock_engine,
        use_llm=True,
    )

    res = orc.recommend(
        location="Bangalore",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0,
        additional_preferences="quiet",
        top_k=3,
    )

    assert len(res.items) == 0
    assert res.message == "No restaurants found"
    assert res.candidates_considered == 0
    mock_engine.rank_and_explain.assert_not_called()


def test_orchestrator_llm_failure_degraded():
    mock_filter = MagicMock()
    mock_filter.find_candidates.return_value = FilterResult(
        candidates=[
            {
                "restaurant_id": "r1",
                "name": "Test Restaurant",
                "city": "Bangalore",
                "cuisines": "North Indian",
            }
        ],
        total_matched=1,
    )

    mock_engine = MagicMock()
    mock_engine.rank_and_explain.side_effect = Exception("LLM connection timed out")

    orc = RecommendationOrchestrator(
        preference_filter=mock_filter,
        llm_engine=mock_engine,
        use_llm=True,
    )

    res = orc.recommend(
        location="Bangalore",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0,
        additional_preferences=None,
        top_k=3,
    )

    assert res.degraded
    assert len(res.items) == 1
    assert "explanation" in res.items[0]
    assert len(res.items[0]["explanation"]) > 0  # fallback stub explanation is populated
