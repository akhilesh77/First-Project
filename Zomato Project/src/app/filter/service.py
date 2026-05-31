"""Preference filter: hard SQL filters + deterministic ranking."""

from __future__ import annotations

import logging
from typing import List, Optional

from app.config import get_database_path, get_max_candidates
from app.data.city import normalize_metro_city
from app.data.repository import RestaurantRepository
from app.filter.models import CANDIDATE_DISPLAY_FIELDS, FilterResult, UserPreferences
from app.filter.scoring import soft_match_score, tokenize_preferences

logger = logging.getLogger(__name__)

_EMPTY_MESSAGE = (
    "No restaurants matched your filters. Try lowering the minimum rating, "
    "choosing a different budget band, or broadening the cuisine."
)


class PreferenceFilter:
    """Apply hard filters and return a bounded, deterministically ranked candidate list."""

    def __init__(
        self,
        repository: Optional[RestaurantRepository] = None,
        max_candidates: Optional[int] = None,
    ) -> None:
        self._repository = repository
        self._max_candidates = max_candidates

    @property
    def repository(self) -> RestaurantRepository:
        if self._repository is None:
            self._repository = RestaurantRepository(get_database_path())
        return self._repository

    @property
    def max_candidates(self) -> int:
        if self._max_candidates is None:
            self._max_candidates = get_max_candidates()
        return self._max_candidates

    def find_candidates(self, preferences: UserPreferences) -> FilterResult:
        location_input = (preferences.location or "").strip()
        city = normalize_metro_city(location_input)
        locality: str | None = None

        # If the normalized result matches a known metro, treat as city-level search.
        # Otherwise, treat the raw input as a locality/neighborhood name and
        # search across all cities that contain restaurants in that area.
        from app.data.city import KNOWN_METROS

        if city and city in KNOWN_METROS:
            # Pure city search (e.g. "Bangalore", "Delhi")
            locality = None
        elif location_input:
            # Locality search — try to find the parent city from the database
            locality = location_input
            resolved_city = self._resolve_city_for_locality(locality)
            if resolved_city:
                city = resolved_city
            else:
                # Last resort: try as a metro anyway
                city = city or location_input.strip().title()

        if not city:
            return FilterResult(
                candidates=[],
                total_matched=0,
                message="Could not resolve location to a known city.",
            )

        cuisine_pattern = f"%{preferences.cuisine.strip()}%"
        cap = preferences.max_candidates or self.max_candidates

        rows, total = self.repository.query_by_preferences(
            city=city,
            budget_band=preferences.budget,
            cuisine_pattern=cuisine_pattern,
            min_rating=preferences.min_rating,
            locality=locality,
        )

        if total == 0:
            return FilterResult(candidates=[], total_matched=0, message=_EMPTY_MESSAGE)

        ranked = self._rank_rows(rows, preferences)
        deduped = self._deduplicate_rows(ranked)
        truncated = len(deduped) > cap
        candidates = [self._to_candidate_dict(row) for row in deduped[:cap]]

        return FilterResult(
            candidates=candidates,
            total_matched=total,
            truncated=truncated,
        )

    def _resolve_city_for_locality(self, locality: str) -> str | None:
        """Look up which metro city contains restaurants in the given locality."""
        conn = self.repository.connect()
        try:
            row = conn.execute(
                """
                SELECT city FROM restaurants
                WHERE (neighborhood LIKE ? COLLATE NOCASE
                       OR listing_area LIKE ? COLLATE NOCASE)
                LIMIT 1
                """,
                (f"%{locality}%", f"%{locality}%"),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    @staticmethod
    def _deduplicate_rows(rows: List[dict]) -> List[dict]:
        """
        Remove duplicate restaurants by normalized (name, city).

        The Zomato dataset often has the same physical restaurant listed with
        different URLs, producing different restaurant_ids. This deduplication
        keeps the first (highest-ranked) occurrence.
        """
        seen: set = set()
        unique: List[dict] = []
        for row in rows:
            name = (row.get("name") or "").strip().lower()
            city = (row.get("city") or "").strip().lower()
            key = (name, city)
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return unique

    def _rank_rows(self, rows: List[dict], preferences: UserPreferences) -> List[dict]:
        pref_tokens = tokenize_preferences(preferences.additional_preferences)

        def sort_key(row: dict) -> tuple:
            soft = soft_match_score(row, pref_tokens)
            rating = row.get("aggregate_rating")
            rating_sort = -(rating if rating is not None else -1.0)
            votes = row.get("votes")
            votes_sort = -(votes if votes is not None else 0)
            rid = row.get("restaurant_id") or ""
            return (-soft, rating_sort, votes_sort, rid)

        return sorted(rows, key=sort_key)

    @staticmethod
    def _to_candidate_dict(row: dict) -> dict:
        return {field: row.get(field) for field in CANDIDATE_DISPLAY_FIELDS}

