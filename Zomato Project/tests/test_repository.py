"""SQLite repository tests."""

from pathlib import Path

import pandas as pd

from app.data.constants import CANONICAL_COLUMNS
from app.data.repository import RestaurantRepository


def test_replace_all_and_stats(tmp_path: Path):
    db = tmp_path / "test.db"
    repo = RestaurantRepository(db)
    df = pd.DataFrame(
        [
            {
                "restaurant_id": "abc123",
                "name": "Test Place",
                "city": "Bangalore",
                "listing_area": "Btm",
                "neighborhood": "Koramangala",
                "address": "123 St",
                "cuisines": "North Indian",
                "cuisine_tokens": '["north indian"]',
                "aggregate_rating": 4.5,
                "votes": 100,
                "cost_for_two": 800.0,
                "budget_band": "medium",
                "rest_type": "Casual Dining",
                "dish_liked": "Biryani",
                "additional_text": "Type: Casual Dining",
                "source_url": "https://example.com/r",
            }
        ],
        columns=CANONICAL_COLUMNS,
    )
    inserted = repo.replace_all(df)
    assert inserted == 1
    stats = repo.get_stats()
    assert stats["row_count"] == 1
    assert stats["budget_band_counts"]["medium"] == 1
