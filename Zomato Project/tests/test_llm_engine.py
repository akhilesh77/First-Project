"""RecommendationLLMEngine tests with mocked Grok client."""

from unittest.mock import MagicMock

import pytest

from app.llm.client import GrokClientError
from app.llm.engine import RecommendationLLMEngine


def _candidates():
    return [
        {
            "restaurant_id": "r1",
            "name": "Spice Villa",
            "city": "Bangalore",
            "cuisines": "North Indian",
            "aggregate_rating": 4.5,
            "cost_for_two": 800.0,
            "budget_band": "medium",
        },
    ]


def test_engine_uses_grok_response():
    mock_client = MagicMock()
    mock_client.chat_completion.return_value = (
        '{"summary": "Nice pick.", "rankings": ['
        '{"restaurant_id": "r1", "explanation": "Great North Indian spot."}]}'
    )
    engine = RecommendationLLMEngine(client=mock_client)
    result = engine.rank_and_explain(
        location="Bangalore",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0,
        additional_preferences=None,
        candidates=_candidates(),
        top_k=1,
    )
    mock_client.chat_completion.assert_called_once()
    assert result.summary == "Nice pick."
    assert len(result.items) == 1
    assert "North Indian" in result.items[0]["explanation"]


def test_engine_fallback_on_grok_error():
    mock_client = MagicMock()
    mock_client.chat_completion.side_effect = GrokClientError("timeout")
    engine = RecommendationLLMEngine(client=mock_client)
    result = engine.rank_and_explain(
        location="Bangalore",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0,
        additional_preferences=None,
        candidates=_candidates(),
        top_k=1,
    )
    assert result.parse_failed
    assert len(result.items) == 1
