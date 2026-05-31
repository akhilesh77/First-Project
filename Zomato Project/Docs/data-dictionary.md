# Data dictionary (Phase 1)

Source dataset: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) (~51,717 rows).

Persisted store: SQLite table `restaurants` (default path `data/restaurants.db`).

## Raw → canonical mapping

| Raw column (HF) | Canonical field | Notes |
|-----------------|-----------------|-------|
| `url` | `source_url`, `restaurant_id` | ID = SHA-256(url)[:16]; fallback hash of name+city+address |
| `name` | `name` | Required; rows without name are dropped |
| `listed_in(city)` | `listing_area` | Listing locality (e.g. BTM, Koramangala 5th Block)—**not** the metro city |
| `address` | `city` | Metro parsed from address tail + aliases (`Bengaluru` → `Bangalore`) |
| `location` | `neighborhood` | Area within city (e.g. Banashankari) |
| `address` | `address` | Full address string |
| `cuisines` | `cuisines`, `cuisine_tokens` | Tokens: lowercase, comma-split JSON array |
| `rate` | `aggregate_rating` | Parsed from `4.1/5`; invalid → `NULL` |
| `approx_cost(for two people)` | `cost_for_two`, `budget_band` | Parsed numeric INR; ranges use midpoint |
| `votes` | `votes` | Integer when parseable |
| `rest_type` | `rest_type`, `additional_text` | Included in explanation text bundle |
| `dish_liked` | `dish_liked`, `additional_text` | Popular dishes |
| `reviews_list` | `additional_text` | Truncated to 500 chars in bundle |

## Canonical schema (`restaurants`)

| Column | Type | Description |
|--------|------|-------------|
| `restaurant_id` | TEXT PK | Stable identifier |
| `name` | TEXT | Restaurant name |
| `city` | TEXT | Metro city for filtering (from `address`) |
| `listing_area` | TEXT | Zomato listing bucket from `listed_in(city)` |
| `neighborhood` | TEXT | Locality from `location` |
| `address` | TEXT | Street address |
| `cuisines` | TEXT | Original cuisine string |
| `cuisine_tokens` | TEXT | JSON array of lowercase tokens |
| `aggregate_rating` | REAL | 0–5 or NULL |
| `votes` | INTEGER | Review vote count or NULL |
| `cost_for_two` | REAL | INR estimate or NULL |
| `budget_band` | TEXT | `low`, `medium`, `high`, or `unknown` |
| `rest_type` | TEXT | e.g. Casual Dining |
| `dish_liked` | TEXT | Popular dishes |
| `additional_text` | TEXT | Combined context for LLM (Phase 4+) |
| `source_url` | TEXT | Zomato URL |

## Indexes

- `idx_restaurants_city`
- `idx_restaurants_budget_band`
- `idx_restaurants_rating`
- `idx_restaurants_cuisines`
- `idx_restaurants_city_budget` (composite)

## Policies

| Topic | Policy |
|-------|--------|
| Null rating | Stored as `NULL`; **excluded** from `aggregate_rating >= min_rating` in Phase 2 |
| Null cost | `budget_band = unknown`; **excluded** from budget filter in Phase 2 |
| Dedupe | By `restaurant_id` (URL hash); keep first row |
| Rows without metro city | Dropped at ingest (~1.8k rows with unparseable addresses) |
| Empty after clean | Ingestion fails with error (no partial serve) |

**Note:** This Hugging Face export is almost entirely **Bangalore** venues. `listed_in(city)` holds listing localities (BTM, Koramangala blocks), not metro names—metro `city` is parsed from `address`.

## Budget bands (INR, cost for two)

| Band | Condition |
|------|-----------|
| `low` | cost ≤ 500 |
| `medium` | 501 ≤ cost ≤ 1000 |
| `high` | cost > 1000 |
| `unknown` | cost is NULL / unparseable |

Defined in `src/app/data/budget.py` (single source of truth).

## Sample queries

After ingest, verify with:

```bash
py -m scripts.ingest -v
```

Or SQLite CLI:

```sql
SELECT COUNT(*) FROM restaurants;

SELECT city, COUNT(*) AS n FROM restaurants GROUP BY city ORDER BY n DESC LIMIT 10;

SELECT name, cuisines, aggregate_rating, cost_for_two, budget_band
FROM restaurants
WHERE city = 'Bangalore'
  AND budget_band = 'medium'
  AND aggregate_rating >= 4.0
  AND cuisines LIKE '%North Indian%'
ORDER BY aggregate_rating DESC
LIMIT 5;
```
