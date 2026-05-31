"""Phase 4 merger and prompt tests."""

import json
import os

from app.llm.prompts import build_messages, preferences_from_request
from app.validation.merger import extract_json_object, merge_llm_rankings


def _candidates():
    return [
        {
            "restaurant_id": "r1",
            "name": "Alpha",
            "city": "Bangalore",
            "cuisines": "North Indian",
            "aggregate_rating": 4.5,
            "cost_for_two": 800.0,
            "budget_band": "medium",
            "neighborhood": "BTM",
        },
        {
            "restaurant_id": "r2",
            "name": "Beta",
            "city": "Bangalore",
            "cuisines": "Italian",
            "aggregate_rating": 4.8,
            "cost_for_two": 1200.0,
            "budget_band": "high",
            "neighborhood": "Indiranagar",
        },
    ]


def test_extract_json_from_fence():
    raw = '```json\n{"rankings": []}\n```'
    assert extract_json_object(raw) == {"rankings": []}


def test_merge_valid_llm_output():
    raw = json.dumps(
        {
            "summary": "Great North Indian picks.",
            "rankings": [
                {"restaurant_id": "r2", "explanation": "Top rated Italian option."},
                {"restaurant_id": "r1", "explanation": "Solid North Indian choice."},
            ],
        }
    )
    result = merge_llm_rankings(
        raw,
        _candidates(),
        top_k=2,
        cuisine_query="Indian",
        budget="medium",
        min_rating=4.0,
        location_query="Bangalore",
    )
    assert not result.parse_failed
    assert result.summary == "Great North Indian picks."
    assert len(result.items) == 2
    assert result.items[0]["restaurant_id"] == "r2"
    assert result.items[0]["name"] == "Beta"
    assert result.items[0]["aggregate_rating"] == 4.8
    assert "Italian" in result.items[0]["explanation"]


def test_merge_rejects_hallucinated_id():
    raw = json.dumps(
        {
            "rankings": [
                {"restaurant_id": "fake99", "explanation": "Not real."},
                {"restaurant_id": "r1", "explanation": "Real."},
            ],
        }
    )
    result = merge_llm_rankings(
        raw,
        _candidates(),
        top_k=2,
        cuisine_query="Indian",
        budget="medium",
        min_rating=4.0,
        location_query="Bangalore",
    )
    assert result.dropped_invalid_ids >= 1
    assert result.items[0]["restaurant_id"] == "r1"


def test_merge_malformed_json_fallback():
    result = merge_llm_rankings(
        "not json at all",
        _candidates(),
        top_k=1,
        cuisine_query="Indian",
        budget="medium",
        min_rating=4.0,
        location_query="Bangalore",
    )
    assert result.parse_failed
    assert len(result.items) == 1
    assert result.items[0]["name"] == "Alpha"


def test_build_messages_shape():
    messages = build_messages(
        preferences=preferences_from_request(
            location="Bangalore",
            budget="medium",
            cuisine="North Indian",
            min_rating=4.0,
        ),
        candidates=_candidates(),
        top_k=3,
    )
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    user_content = json.loads(messages[1]["content"])
    assert user_content["user_preferences"]["location"] == "Bangalore"
    assert len(user_content["candidates"]) == 2
    assert "restaurant_id" in user_content["candidates"][0]


def test_prompt_shape_golden():
    messages = build_messages(
        preferences=preferences_from_request(
            location="Bangalore",
            budget="medium",
            cuisine="North Indian",
            min_rating=4.0,
        ),
        candidates=_candidates(),
        top_k=3,
    )
    
    golden_path = os.path.join(
        os.path.dirname(__file__), "fixtures", "prompt_shape_golden.json"
    )
    
    # If the file does not exist, write it (to generate/update the golden file)
    if not os.path.exists(golden_path):
        os.makedirs(os.path.dirname(golden_path), exist_ok=True)
        with open(golden_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
            
    # Read the expected golden file
    with open(golden_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
        
    assert messages == expected
