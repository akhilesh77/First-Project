"""Phase 2 filter and preference tests."""

from pathlib import Path

import pytest

from app.data.constants import CANONICAL_COLUMNS
from app.data.repository import RestaurantRepository
from app.filter import PreferenceFilter, UserPreferences
from app.filter.scoring import soft_match_score, tokenize_preferences


def _sample_rows():
    return [
        {
            "restaurant_id": "r1",
            "name": "Spice Villa",
            "city": "Bangalore",
            "listing_area": "Btm",
            "neighborhood": "BTM",
            "address": "BTM, Bangalore",
            "cuisines": "North Indian, Chinese",
            "cuisine_tokens": '["north indian", "chinese"]',
            "aggregate_rating": 4.5,
            "votes": 500,
            "cost_for_two": 800.0,
            "budget_band": "medium",
            "rest_type": "Casual Dining",
            "dish_liked": "Biryani",
            "additional_text": "family-friendly dining",
            "source_url": "https://example.com/r1",
        },
        {
            "restaurant_id": "r2",
            "name": "Pizza Hub",
            "city": "Bangalore",
            "listing_area": "Indiranagar",
            "neighborhood": "Indiranagar",
            "address": "Indiranagar, Bangalore",
            "cuisines": "Italian, Fast Food",
            "cuisine_tokens": '["italian", "fast food"]',
            "aggregate_rating": 4.8,
            "votes": 900,
            "cost_for_two": 1200.0,
            "budget_band": "high",
            "rest_type": "Cafe",
            "dish_liked": "Pizza",
            "additional_text": "quick service",
            "source_url": "https://example.com/r2",
        },
        {
            "restaurant_id": "r3",
            "name": "Budget Bites",
            "city": "Bangalore",
            "listing_area": "Jayanagar",
            "neighborhood": "Jayanagar",
            "address": "Jayanagar, Bangalore",
            "cuisines": "North Indian",
            "cuisine_tokens": '["north indian"]',
            "aggregate_rating": None,
            "votes": 50,
            "cost_for_two": 300.0,
            "budget_band": "low",
            "rest_type": "Quick Bites",
            "dish_liked": None,
            "additional_text": None,
            "source_url": "https://example.com/r3",
        },
        {
            "restaurant_id": "r4",
            "name": "Curry Leaf",
            "city": "Bangalore",
            "listing_area": "Koramangala",
            "neighborhood": "Koramangala",
            "address": "Koramangala, Bangalore",
            "cuisines": "South Indian",
            "cuisine_tokens": '["south indian"]',
            "aggregate_rating": 4.2,
            "votes": 200,
            "cost_for_two": 450.0,
            "budget_band": "low",
            "rest_type": "Casual Dining",
            "dish_liked": "Dosa",
            "additional_text": None,
            "source_url": "https://example.com/r4",
        },
    ]


@pytest.fixture
def filter_db(tmp_path: Path):
    db = tmp_path / "filter_test.db"
    repo = RestaurantRepository(db)
    import pandas as pd

    repo.replace_all(pd.DataFrame(_sample_rows(), columns=CANONICAL_COLUMNS))
    return PreferenceFilter(repository=repo, max_candidates=2)


def test_user_preferences_validation():
    with pytest.raises(ValueError):
        UserPreferences(location="", budget="low", cuisine="Italian", min_rating=4.0)
    with pytest.raises(ValueError):
        UserPreferences(location="Delhi", budget="cheap", cuisine="Italian", min_rating=4.0)  # type: ignore[arg-type]


def test_filter_matches_budget_and_cuisine(filter_db: PreferenceFilter):
    prefs = UserPreferences(
        location="Bengaluru",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0,
    )
    result = filter_db.find_candidates(prefs)
    assert result.total_matched == 1
    assert len(result.candidates) == 1
    assert result.candidates[0]["restaurant_id"] == "r1"
    assert result.candidates[0]["name"] == "Spice Villa"


def test_filter_excludes_null_rating(filter_db: PreferenceFilter):
    prefs = UserPreferences(
        location="Bangalore",
        budget="low",
        cuisine="North Indian",
        min_rating=0.0,
    )
    result = filter_db.find_candidates(prefs)
    ids = {c["restaurant_id"] for c in result.candidates}
    assert "r3" not in ids


def test_filter_no_results(filter_db: PreferenceFilter):
    prefs = UserPreferences(
        location="Mumbai",
        budget="low",
        cuisine="North Indian",
        min_rating=4.0,
    )
    result = filter_db.find_candidates(prefs)
    assert result.is_empty
    assert result.message is not None


def test_filter_truncates_and_soft_scores(filter_db: PreferenceFilter):
    prefs = UserPreferences(
        location="bangalore",
        budget="low",
        cuisine="Indian",
        min_rating=4.0,
        additional_preferences="south, dosa",
    )
    result = filter_db.find_candidates(prefs)
    assert result.total_matched >= 1
    assert len(result.candidates) <= 2
    if result.total_matched > 2:
        assert result.truncated


def test_soft_match_score():
    row = {"cuisines": "South Indian", "dish_liked": "Dosa", "additional_text": ""}
    tokens = tokenize_preferences("south indian, dosa")
    assert soft_match_score(row, tokens) >= 2


def test_tokenize_ignores_generic_words():
    assert "food" not in tokenize_preferences("good food, family-friendly")


def test_filter_deduplicates_same_restaurant(tmp_path: Path):
    """Same restaurant with different restaurant_ids should be deduplicated."""
    import pandas as pd

    duplicate_rows = [
        {
            "restaurant_id": "dup1",
            "name": "Spice Villa",
            "city": "Bangalore",
            "listing_area": "BTM",
            "neighborhood": "BTM",
            "address": "BTM, Bangalore",
            "cuisines": "North Indian, Chinese",
            "cuisine_tokens": '["north indian", "chinese"]',
            "aggregate_rating": 4.5,
            "votes": 500,
            "cost_for_two": 800.0,
            "budget_band": "medium",
            "rest_type": "Casual Dining",
            "dish_liked": "Biryani",
            "additional_text": "family-friendly",
            "source_url": "https://example.com/dup1",
        },
        {
            "restaurant_id": "dup2",
            "name": "Spice Villa",
            "city": "Bangalore",
            "listing_area": "BTM",
            "neighborhood": "BTM",
            "address": "BTM Layout, Bangalore",
            "cuisines": "North Indian, Chinese",
            "cuisine_tokens": '["north indian", "chinese"]',
            "aggregate_rating": 4.3,
            "votes": 300,
            "cost_for_two": 750.0,
            "budget_band": "medium",
            "rest_type": "Casual Dining",
            "dish_liked": "Biryani",
            "additional_text": "family dining",
            "source_url": "https://example.com/dup2",
        },
        {
            "restaurant_id": "dup3",
            "name": "Spice Villa",
            "city": "Bangalore",
            "listing_area": "BTM",
            "neighborhood": "BTM",
            "address": "BTM 2nd Stage, Bangalore",
            "cuisines": "North Indian, Chinese",
            "cuisine_tokens": '["north indian", "chinese"]',
            "aggregate_rating": 4.1,
            "votes": 100,
            "cost_for_two": 800.0,
            "budget_band": "medium",
            "rest_type": "Casual Dining",
            "dish_liked": None,
            "additional_text": None,
            "source_url": "https://example.com/dup3",
        },
    ]

    db = tmp_path / "dedup_test.db"
    repo = RestaurantRepository(db)
    repo.replace_all(pd.DataFrame(duplicate_rows, columns=CANONICAL_COLUMNS))

    pf = PreferenceFilter(repository=repo, max_candidates=10)
    prefs = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0,
    )
    result = pf.find_candidates(prefs)

    # All three match the filters, but dedup should keep only 1
    assert len(result.candidates) == 1
    # The highest-rated one (dup1, rating=4.5) should be the survivor
    assert result.candidates[0]["restaurant_id"] == "dup1"
    assert result.candidates[0]["name"] == "Spice Villa"

