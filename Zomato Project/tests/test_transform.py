"""Unit tests for transform and budget mapping."""

import pandas as pd

from app.data.budget import (
    BUDGET_HIGH,
    BUDGET_LOW,
    BUDGET_MEDIUM,
    BUDGET_UNKNOWN,
    cost_to_budget_band,
)
from app.data.constants import (
    COL_ADDRESS,
    COL_COST,
    COL_CUISINES,
    COL_LISTED_CITY,
    COL_NAME,
    COL_RATE,
    COL_URL,
)
from app.data.transform import (
    extract_metro_city,
    parse_cost,
    parse_rating,
    tokenize_cuisines,
    transform_dataframe,
)


def test_parse_rating():
    assert parse_rating("4.1/5") == 4.1
    assert parse_rating("-") is None
    assert parse_rating("NEW") is None
    assert parse_rating(None) is None


def test_parse_cost():
    assert parse_cost("800") == 800.0
    assert parse_cost("1,200") == 1200.0
    assert parse_cost("300-400") == 350.0
    assert parse_cost("-") is None


def test_budget_bands():
    assert cost_to_budget_band(400) == BUDGET_LOW
    assert cost_to_budget_band(500) == BUDGET_LOW
    assert cost_to_budget_band(800) == BUDGET_MEDIUM
    assert cost_to_budget_band(1000) == BUDGET_MEDIUM
    assert cost_to_budget_band(1500) == BUDGET_MEDIUM
    assert cost_to_budget_band(1600) == BUDGET_HIGH
    assert cost_to_budget_band(None) == BUDGET_UNKNOWN


def test_tokenize_cuisines():
    assert tokenize_cuisines("North Indian, Chinese") == ["north indian", "chinese"]
    assert tokenize_cuisines("") == []


def test_extract_metro_city_from_address():
    assert extract_metro_city("942, Banashankari, Bangalore", "BTM") == "Bangalore"
    assert extract_metro_city("Some place, Bengaluru", None) == "Bangalore"
    assert extract_metro_city(None, None) is None


def test_transform_dedupes_by_url():
    df = pd.DataFrame(
        [
            {
                COL_URL: "https://example.com/a",
                COL_NAME: "Cafe A",
                COL_LISTED_CITY: "BTM",
                COL_ADDRESS: "1st Main, Banashankari, Bangalore",
                COL_RATE: "4.0/5",
                COL_COST: "600",
                COL_CUISINES: "Italian",
            },
            {
                COL_URL: "https://example.com/a",
                COL_NAME: "Cafe A Duplicate",
                COL_LISTED_CITY: "BTM",
                COL_ADDRESS: "1st Main, Banashankari, Bangalore",
                COL_RATE: "3.0/5",
                COL_COST: "600",
                COL_CUISINES: "Italian",
            },
        ]
    )
    out = transform_dataframe(df)
    assert len(out) == 1
    assert out.iloc[0]["name"] == "Cafe A"
    assert out.iloc[0]["city"] == "Bangalore"
