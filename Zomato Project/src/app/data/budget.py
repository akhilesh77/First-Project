"""Budget band mapping (single source of truth)."""

from __future__ import annotations

from typing import Optional

# INR approximate cost for two (see Docs/data-dictionary.md)
BUDGET_LOW_MAX = 500
BUDGET_MEDIUM_MAX = 1500

BUDGET_LOW = "low"
BUDGET_MEDIUM = "medium"
BUDGET_HIGH = "high"
BUDGET_UNKNOWN = "unknown"

VALID_BUDGET_BANDS = {BUDGET_LOW, BUDGET_MEDIUM, BUDGET_HIGH, BUDGET_UNKNOWN}

# Canonical budget range display formatting (Indian Rupee)
BUDGET_DISPLAY = {
    BUDGET_LOW: "₹200 - ₹500",
    BUDGET_MEDIUM: "₹500 - ₹1500",
    BUDGET_HIGH: "₹1500+",
    BUDGET_UNKNOWN: "Unknown",
}



def cost_to_budget_band(cost_for_two: Optional[float]) -> str:
    """Map numeric cost to low | medium | high | unknown."""
    if cost_for_two is None:
        return BUDGET_UNKNOWN
    if cost_for_two <= BUDGET_LOW_MAX:
        return BUDGET_LOW
    if cost_for_two <= BUDGET_MEDIUM_MAX:
        return BUDGET_MEDIUM
    return BUDGET_HIGH
