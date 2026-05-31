"""Deterministic soft scoring for additional_preferences (sort only)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_TOKEN_SPLIT_RE = re.compile(r"[,;]+|\s+")
_GENERIC_TOKENS = frozenset({"a", "an", "the", "and", "or", "for", "with", "food", "restaurant"})


def tokenize_preferences(text: Optional[str]) -> List[str]:
    if not text or not text.strip():
        return []
    tokens = [_t.lower() for _t in _TOKEN_SPLIT_RE.split(text.strip()) if _t.strip()]
    return [t for t in tokens if t not in _GENERIC_TOKENS and len(t) > 1]


def soft_match_score(row: Dict[str, Any], preference_tokens: List[str]) -> int:
    """
    Count how many preference tokens appear in searchable text fields.
    Higher is better; used only for ordering before cap.
    """
    if not preference_tokens:
        return 0

    haystack_parts = [
        row.get("cuisines") or "",
        row.get("dish_liked") or "",
        row.get("rest_type") or "",
        row.get("additional_text") or "",
        row.get("neighborhood") or "",
        row.get("listing_area") or "",
    ]
    haystack = " ".join(haystack_parts).lower()
    return sum(1 for token in preference_tokens if token in haystack)
