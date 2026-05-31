"""Parse Grok JSON output and merge with authoritative datastore fields."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from app.api.stub import build_stub_explanation

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


@dataclass
class MergeResult:
    """Ranked rows with explanations ready for API mapping."""

    items: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None
    parse_failed: bool = False
    dropped_invalid_ids: int = 0


def extract_json_object(raw: str) -> Dict[str, Any]:
    """Parse JSON from model output, stripping optional markdown fences."""
    text = raw.strip()
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def merge_llm_rankings(
    raw_llm_output: str,
    candidates: List[Dict[str, Any]],
    *,
    top_k: int,
    cuisine_query: str,
    budget: str,
    min_rating: float,
    location_query: str,
) -> MergeResult:
    """
    Validate Grok rankings and attach explanations.

    Authoritative fields (name, rating, cost, cuisines) always come from candidates.
    """
    candidate_by_id = {c["restaurant_id"]: c for c in candidates if c.get("restaurant_id")}
    valid_ids: Set[str] = set(candidate_by_id.keys())

    try:
        payload = extract_json_object(raw_llm_output)
    except (json.JSONDecodeError, TypeError, ValueError):
        return _fallback_merge(
            candidates,
            top_k=top_k,
            cuisine_query=cuisine_query,
            budget=budget,
            min_rating=min_rating,
            location_query=location_query,
            parse_failed=True,
        )

    summary = payload.get("summary")
    if isinstance(summary, str):
        summary = summary.strip() or None
    else:
        summary = None

    rankings = payload.get("rankings")
    if not isinstance(rankings, list):
        return _fallback_merge(
            candidates,
            top_k=top_k,
            cuisine_query=cuisine_query,
            budget=budget,
            min_rating=min_rating,
            location_query=location_query,
            parse_failed=True,
        )

    seen: Set[str] = set()
    items: List[Dict[str, Any]] = []
    dropped = 0

    for entry in rankings:
        if not isinstance(entry, dict):
            continue
        rid = entry.get("restaurant_id")
        if not rid or rid not in valid_ids or rid in seen:
            dropped += 1
            continue
        seen.add(rid)
        row = dict(candidate_by_id[rid])
        explanation = entry.get("explanation")
        if not explanation or not str(explanation).strip():
            explanation = build_stub_explanation(
                row,
                cuisine_query=cuisine_query,
                budget=budget,
                min_rating=min_rating,
                location_query=location_query,
            )
        row["explanation"] = str(explanation).strip()
        items.append(row)
        if len(items) >= top_k:
            break

    if len(items) < top_k:
        items, pad_dropped = _pad_from_candidates(
            items, candidates, top_k, seen, valid_ids
        )
        dropped += pad_dropped

    return MergeResult(
        items=items,
        summary=summary,
        parse_failed=False,
        dropped_invalid_ids=dropped,
    )


def _pad_from_candidates(
    items: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    top_k: int,
    seen: Set[str],
    valid_ids: Set[str],
) -> tuple[List[Dict[str, Any]], int]:
    """Fill remaining slots from deterministic candidate order."""
    dropped = 0
    for row in candidates:
        rid = row.get("restaurant_id")
        if not rid or rid in seen or rid not in valid_ids:
            continue
        seen.add(rid)
        padded = dict(row)
        if "explanation" not in padded:
            padded["explanation"] = ""
        items.append(padded)
        if len(items) >= top_k:
            break
    return items, dropped


def _fallback_merge(
    candidates: List[Dict[str, Any]],
    *,
    top_k: int,
    cuisine_query: str,
    budget: str,
    min_rating: float,
    location_query: str,
    parse_failed: bool,
) -> MergeResult:
    items = []
    seen: set = set()
    for row in candidates:
        # Deduplicate by normalized (name, cuisines) before building fallback items
        name = (row.get("name") or "").strip().lower()
        cuisines = (row.get("cuisines") or "").strip().lower()
        key = (name, cuisines)
        if key in seen:
            continue
        seen.add(key)

        merged = dict(row)
        merged["explanation"] = build_stub_explanation(
            row,
            cuisine_query=cuisine_query,
            budget=budget,
            min_rating=min_rating,
            location_query=location_query,
        )
        items.append(merged)
        if len(items) >= top_k:
            break
    return MergeResult(items=items, summary=None, parse_failed=parse_failed, dropped_invalid_ids=0)

