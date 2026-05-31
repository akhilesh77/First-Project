"""Load, clean, and map Hugging Face rows to the canonical restaurant schema."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional

import pandas as pd
from datasets import load_dataset

from app.data.budget import cost_to_budget_band
from app.data.city import CITY_ALIASES, KNOWN_METROS, normalize_metro_city
from app.data.constants import (
    CANONICAL_COLUMNS,
    COL_ADDRESS,
    COL_COST,
    COL_CUISINES,
    COL_DISH_LIKED,
    COL_LISTED_CITY,
    COL_LOCATION,
    COL_NAME,
    COL_RATE,
    COL_REST_TYPE,
    COL_REVIEWS,
    COL_URL,
    COL_VOTES,
)

# Ratings that cannot be parsed are stored as NULL and excluded from min_rating filters.
_INVALID_RATE_TOKENS = {"-", "new", "none", "nan", ""}

_COST_RANGE_RE = re.compile(r"(\d[\d,]*)")
_RATE_RE = re.compile(r"(\d+(?:\.\d+)?)")

def _clean_str(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text if text else None


def _normalize_city_label(label: Optional[str]) -> Optional[str]:
    return normalize_metro_city(label)


def extract_metro_city(address: Optional[str], listing_area: Optional[str]) -> Optional[str]:
    """
    Derive metro city for filtering.

    The HF column `listed_in(city)` is a listing locality (e.g. BTM), not a metro.
    Primary source: last segment of `address`; fallback: scan address for known metros.
    """
    if address:
        parts = [p.strip() for p in str(address).split(",") if p.strip()]
        if parts:
            tail = _normalize_city_label(parts[-1])
            if tail in KNOWN_METROS:
                return tail
        lowered = str(address).lower()
        for alias, metro in CITY_ALIASES.items():
            if alias in lowered:
                return metro
    if listing_area:
        area_lower = listing_area.strip().lower()
        for alias, metro in CITY_ALIASES.items():
            if alias in area_lower:
                return metro
    return None


def parse_rating(rate_raw: Any) -> Optional[float]:
    """Parse values like '4.1/5' into a float; invalid values become None."""
    text = _clean_str(rate_raw)
    if not text:
        return None
    lowered = text.lower()
    if lowered in _INVALID_RATE_TOKENS:
        return None
    match = _RATE_RE.search(lowered.replace(",", ""))
    if not match:
        return None
    value = float(match.group(1))
    if value < 0 or value > 5:
        return None
    return round(value, 2)


def parse_cost(cost_raw: Any) -> Optional[float]:
    """
    Parse cost strings: '800', '1,200', '300-400' (uses midpoint for ranges).
    """
    text = _clean_str(cost_raw)
    if not text:
        return None
    lowered = text.lower()
    if lowered in _INVALID_RATE_TOKENS:
        return None

    numbers = [int(n.replace(",", "")) for n in _COST_RANGE_RE.findall(text)]
    if not numbers:
        return None
    if len(numbers) == 1:
        return float(numbers[0])
    return float(sum(numbers) / len(numbers))


def tokenize_cuisines(cuisines_raw: Any) -> List[str]:
    text = _clean_str(cuisines_raw)
    if not text:
        return []
    parts = [p.strip().lower() for p in text.split(",")]
    return [p for p in parts if p]


def _make_restaurant_id(url: Optional[str], name: str, city: str, address: Optional[str]) -> str:
    if url:
        key = url.strip()
    else:
        key = "|".join([name.strip().lower(), city.strip().lower(), (address or "").strip().lower()])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _build_additional_text(
    rest_type: Optional[str],
    dish_liked: Optional[str],
    reviews_list: Any,
    max_review_chars: int = 500,
) -> Optional[str]:
    parts: List[str] = []
    if rest_type:
        parts.append(f"Type: {rest_type}")
    if dish_liked:
        parts.append(f"Popular dishes: {dish_liked}")
    review_text = _clean_str(reviews_list)
    if review_text:
        snippet = review_text[:max_review_chars]
        if len(review_text) > max_review_chars:
            snippet += "..."
        parts.append(f"Reviews excerpt: {snippet}")
    return " | ".join(parts) if parts else None


def _row_to_canonical(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = _clean_str(row.get(COL_NAME))
    address = _clean_str(row.get(COL_ADDRESS))
    listing_area_raw = _clean_str(row.get(COL_LISTED_CITY))
    listing_area = _normalize_city_label(listing_area_raw) if listing_area_raw else None
    city = extract_metro_city(address, listing_area_raw)
    if not name or not city:
        return None

    url = _clean_str(row.get(COL_URL))
    neighborhood = _clean_str(row.get(COL_LOCATION))
    cuisines = _clean_str(row.get(COL_CUISINES))
    tokens = tokenize_cuisines(cuisines)
    rating = parse_rating(row.get(COL_RATE))
    cost = parse_cost(row.get(COL_COST))

    votes_raw = row.get(COL_VOTES)
    votes: Optional[int] = None
    if votes_raw is not None and not (isinstance(votes_raw, float) and pd.isna(votes_raw)):
        try:
            votes = int(votes_raw)
        except (TypeError, ValueError):
            votes = None

    return {
        "restaurant_id": _make_restaurant_id(url, name, city, address),
        "name": name,
        "city": city,
        "listing_area": listing_area,
        "neighborhood": neighborhood,
        "address": address,
        "cuisines": cuisines,
        "cuisine_tokens": json.dumps(tokens, ensure_ascii=False),
        "aggregate_rating": rating,
        "votes": votes,
        "cost_for_two": cost,
        "budget_band": cost_to_budget_band(cost),
        "rest_type": _clean_str(row.get(COL_REST_TYPE)),
        "dish_liked": _clean_str(row.get(COL_DISH_LIKED)),
        "additional_text": _build_additional_text(
            _clean_str(row.get(COL_REST_TYPE)),
            _clean_str(row.get(COL_DISH_LIKED)),
            row.get(COL_REVIEWS),
        ),
        "source_url": url,
    }


def load_raw_dataframe(dataset_id: str) -> pd.DataFrame:
    """Download and load the Hugging Face train split into a pandas DataFrame."""
    dataset = load_dataset(dataset_id, split="train")
    return dataset.to_pandas()


def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw rows to canonical schema and deduplicate."""
    records: List[Dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        canonical = _row_to_canonical(row)
        if canonical:
            records.append(canonical)

    if not records:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    out = pd.DataFrame(records)
    before = len(out)
    out = out.drop_duplicates(subset=["restaurant_id"], keep="first")
    out.attrs["dedupe_removed"] = before - len(out)
    return out


def summarize_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Build ingestion statistics for logging and reports."""
    return {
        "row_count": int(len(df)),
        "null_rating_count": int(df["aggregate_rating"].isna().sum()) if len(df) else 0,
        "null_cost_count": int(df["cost_for_two"].isna().sum()) if len(df) else 0,
        "budget_band_counts": df["budget_band"].value_counts().to_dict() if len(df) else {},
        "city_count": int(df["city"].nunique()) if len(df) else 0,
        "top_cities": df["city"].value_counts().head(10).to_dict() if len(df) else {},
    }
