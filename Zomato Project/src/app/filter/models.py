"""User preference and filter result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from app.data.budget import BUDGET_HIGH, BUDGET_LOW, BUDGET_MEDIUM

BudgetBand = Literal["low", "medium", "high"]
VALID_USER_BUDGETS = {BUDGET_LOW, BUDGET_MEDIUM, BUDGET_HIGH}

# Fields returned to UI / later LLM stages (Phase 2 exit criteria).
CANDIDATE_DISPLAY_FIELDS = [
    "restaurant_id",
    "name",
    "city",
    "listing_area",
    "neighborhood",
    "cuisines",
    "aggregate_rating",
    "cost_for_two",
    "budget_band",
    "votes",
    "additional_text",
]


@dataclass(frozen=True)
class UserPreferences:
    """Structured user inputs from context.md."""

    location: str
    budget: BudgetBand
    cuisine: str
    min_rating: float
    additional_preferences: Optional[str] = None
    max_candidates: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.location or not self.location.strip():
            raise ValueError("location is required")
        if self.budget not in VALID_USER_BUDGETS:
            raise ValueError(f"budget must be one of {sorted(VALID_USER_BUDGETS)}")
        if not self.cuisine or not self.cuisine.strip():
            raise ValueError("cuisine is required")
        if self.min_rating < 0 or self.min_rating > 5:
            raise ValueError("min_rating must be between 0 and 5")
        if self.max_candidates is not None and self.max_candidates < 1:
            raise ValueError("max_candidates must be at least 1")


@dataclass
class FilterResult:
    """Bounded candidate list after deterministic filter + rank."""

    candidates: List[Dict[str, Any]] = field(default_factory=list)
    total_matched: int = 0
    message: Optional[str] = None
    truncated: bool = False

    @property
    def is_empty(self) -> bool:
        return len(self.candidates) == 0
