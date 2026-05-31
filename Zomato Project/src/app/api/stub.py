"""Template explanations until LLM integration (Phase 4+)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.data.budget import BUDGET_DISPLAY


def format_display_location(city: Optional[str], neighborhood: Optional[str]) -> str:
    if city and neighborhood and neighborhood.lower() != city.lower():
        return f"{city} ({neighborhood})"
    return city or neighborhood or "Unknown"


def format_estimated_cost(cost_for_two: Optional[float], budget_band: Optional[str]) -> Optional[float]:
    if cost_for_two is not None:
        return float(cost_for_two)
    return None


def build_stub_explanation(
    candidate: Dict[str, Any],
    *,
    cuisine_query: str,
    budget: str,
    min_rating: float,
    location_query: str,
) -> str:
    name = candidate.get("name", "This restaurant")
    cuisines = candidate.get("cuisines") or cuisine_query
    rating = candidate.get("aggregate_rating")
    cost = candidate.get("cost_for_two")
    band = candidate.get("budget_band") or budget
    area = candidate.get("neighborhood") or candidate.get("listing_area") or location_query

    display_range = BUDGET_DISPLAY.get(band, band)

    parts = [
        f"{name} serves {cuisines}",
        f"in {area}",
        f"with a {display_range} budget profile",
    ]
    if rating is not None:
        parts.append(f"rated {rating}/5 (your minimum was {min_rating})")
    if cost is not None:
        parts.append(f"at roughly ₹{int(cost)} for two")
    parts.append("— matched by your filters (AI ranking coming in a later release).")
    return " ".join(parts) + ""

