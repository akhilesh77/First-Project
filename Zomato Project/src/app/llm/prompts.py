"""Prompt construction for Grok ranking and explanations."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

SYSTEM_PROMPT = """You are a restaurant recommendation assistant for Zomato-style data.
You must ONLY rank and explain restaurants from the candidate list provided.
Do NOT invent restaurants or restaurant_id values.
Respond with valid JSON only (no markdown fences), matching this schema:
{{
  "summary": "optional short overview of trade-offs for the user",
  "rankings": [
    {{"restaurant_id": "<id from list>", "explanation": "1-3 sentences why this fits the user"}}
  ]
}}
Include at most {top_k} items in rankings, best first.
Reference real attributes from the candidate data (cuisine, rating, cost, area)."""


def _compact_candidate(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "restaurant_id": row.get("restaurant_id"),
        "name": row.get("name"),
        "city": row.get("city"),
        "neighborhood": row.get("neighborhood"),
        "listing_area": row.get("listing_area"),
        "cuisines": row.get("cuisines"),
        "aggregate_rating": row.get("aggregate_rating"),
        "cost_for_two": row.get("cost_for_two"),
        "budget_band": row.get("budget_band"),
        "votes": row.get("votes"),
        "rest_type": row.get("rest_type"),
        "dish_liked": row.get("dish_liked"),
    }


def build_messages(
    *,
    preferences: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    top_k: int,
) -> List[Dict[str, str]]:
    """Build chat messages for Grok (OpenAI-compatible)."""
    compact = [_compact_candidate(c) for c in candidates]
    user_payload = {
        "user_preferences": preferences,
        "candidates": compact,
        "instructions": (
            f"Rank up to {top_k} restaurants from candidates for this user. "
            "Use only restaurant_id values from candidates."
        ),
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(top_k=top_k)},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def preferences_from_request(
    *,
    location: str,
    budget: str,
    cuisine: str,
    min_rating: float,
    additional_preferences: Optional[str] = None,
) -> Dict[str, Any]:
    prefs: Dict[str, Any] = {
        "location": location,
        "budget": budget,
        "cuisine": cuisine,
        "min_rating": min_rating,
    }
    if additional_preferences:
        prefs["additional_preferences"] = additional_preferences
    return prefs
