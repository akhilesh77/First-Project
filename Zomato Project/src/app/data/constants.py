"""Raw Hugging Face column names and canonical field identifiers."""

# Raw dataset columns (ManikaSaini/zomato-restaurant-recommendation)
COL_URL = "url"
COL_ADDRESS = "address"
COL_NAME = "name"
COL_RATE = "rate"
COL_VOTES = "votes"
COL_LOCATION = "location"
COL_REST_TYPE = "rest_type"
COL_DISH_LIKED = "dish_liked"
COL_CUISINES = "cuisines"
COL_COST = "approx_cost(for two people)"
COL_REVIEWS = "reviews_list"
COL_LISTED_CITY = "listed_in(city)"

RAW_COLUMNS = [
    COL_URL,
    COL_ADDRESS,
    COL_NAME,
    COL_RATE,
    COL_VOTES,
    COL_LOCATION,
    COL_REST_TYPE,
    COL_DISH_LIKED,
    COL_CUISINES,
    COL_COST,
    COL_REVIEWS,
    COL_LISTED_CITY,
]

# Canonical restaurant fields (persisted in SQLite)
CANONICAL_COLUMNS = [
    "restaurant_id",
    "name",
    "city",
    "listing_area",
    "neighborhood",
    "address",
    "cuisines",
    "cuisine_tokens",
    "aggregate_rating",
    "votes",
    "cost_for_two",
    "budget_band",
    "rest_type",
    "dish_liked",
    "additional_text",
    "source_url",
]
