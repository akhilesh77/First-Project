"""SQLite persistence for canonical restaurant records."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.data.constants import CANONICAL_COLUMNS

CREATE_RESTAURANTS_SQL = """
CREATE TABLE IF NOT EXISTS restaurants (
    restaurant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    listing_area TEXT,
    neighborhood TEXT,
    address TEXT,
    cuisines TEXT,
    cuisine_tokens TEXT NOT NULL,
    aggregate_rating REAL,
    votes INTEGER,
    cost_for_two REAL,
    budget_band TEXT NOT NULL,
    rest_type TEXT,
    dish_liked TEXT,
    additional_text TEXT,
    source_url TEXT
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants(city);",
    "CREATE INDEX IF NOT EXISTS idx_restaurants_budget_band ON restaurants(budget_band);",
    "CREATE INDEX IF NOT EXISTS idx_restaurants_rating ON restaurants(aggregate_rating);",
    "CREATE INDEX IF NOT EXISTS idx_restaurants_cuisines ON restaurants(cuisines);",
    "CREATE INDEX IF NOT EXISTS idx_restaurants_city_budget ON restaurants(city, budget_band);",
    "CREATE INDEX IF NOT EXISTS idx_restaurants_listing_area ON restaurants(listing_area);",
]

SAMPLE_QUERIES = {
    "count_all": "SELECT COUNT(*) AS n FROM restaurants;",
    "by_city": (
        "SELECT city, COUNT(*) AS n FROM restaurants "
        "GROUP BY city ORDER BY n DESC LIMIT 10;"
    ),
    "filter_example": (
        "SELECT name, city, cuisines, aggregate_rating, cost_for_two, budget_band "
        "FROM restaurants "
        "WHERE city = ? AND budget_band = ? AND aggregate_rating >= ? "
        "AND cuisines LIKE ? "
        "ORDER BY aggregate_rating DESC LIMIT 5;"
    ),
}


class RestaurantRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(CREATE_RESTAURANTS_SQL)
        for stmt in CREATE_INDEXES_SQL:
            conn.execute(stmt)
        conn.commit()

    def replace_all(self, df: pd.DataFrame, conn: Optional[sqlite3.Connection] = None) -> int:
        """Replace restaurant table contents with the given canonical DataFrame."""
        own_conn = conn is None
        if own_conn:
            conn = self.connect()
        assert conn is not None

        try:
            conn.execute("DROP TABLE IF EXISTS restaurants;")
            self.initialize_schema(conn)
            if df.empty:
                conn.commit()
                return 0

            rows = df[CANONICAL_COLUMNS].to_dict(orient="records")
            placeholders = ", ".join(["?"] * len(CANONICAL_COLUMNS))
            columns_sql = ", ".join(CANONICAL_COLUMNS)
            insert_sql = f"INSERT INTO restaurants ({columns_sql}) VALUES ({placeholders})"
            conn.executemany(
                insert_sql,
                [tuple(row[col] for col in CANONICAL_COLUMNS) for row in rows],
            )
            conn.commit()
            return len(rows)
        finally:
            if own_conn:
                conn.close()

    def get_stats(self, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        own_conn = conn is None
        if own_conn:
            conn = self.connect()
        assert conn is not None

        try:
            total = conn.execute("SELECT COUNT(*) FROM restaurants;").fetchone()[0]
            null_ratings = conn.execute(
                "SELECT COUNT(*) FROM restaurants WHERE aggregate_rating IS NULL;"
            ).fetchone()[0]
            null_costs = conn.execute(
                "SELECT COUNT(*) FROM restaurants WHERE cost_for_two IS NULL;"
            ).fetchone()[0]
            bands = conn.execute(
                "SELECT budget_band, COUNT(*) AS n FROM restaurants GROUP BY budget_band;"
            ).fetchall()
            cities = conn.execute(
                "SELECT city, COUNT(*) AS n FROM restaurants "
                "GROUP BY city ORDER BY n DESC LIMIT 10;"
            ).fetchall()
            return {
                "row_count": total,
                "null_rating_count": null_ratings,
                "null_cost_count": null_costs,
                "budget_band_counts": {row[0]: row[1] for row in bands},
                "top_cities": {row[0]: row[1] for row in cities},
            }
        finally:
            if own_conn:
                conn.close()

    def query_by_preferences(
        self,
        *,
        city: str,
        budget_band: str,
        cuisine_pattern: str,
        min_rating: float,
        locality: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Hard filters for Phase 2.

        - city: exact metro match (caller normalizes)
        - budget_band: equality (excludes `unknown`)
        - cuisine: case-insensitive substring on `cuisines`
        - min_rating: NULL ratings excluded (edge-case policy)
        - locality: optional neighborhood/listing_area substring filter
        """
        base_where = """
            WHERE city = ?
              AND budget_band = ?
              AND cuisines LIKE ? COLLATE NOCASE
              AND aggregate_rating IS NOT NULL
              AND aggregate_rating >= ?
        """
        params: list = [city, budget_band, cuisine_pattern, min_rating]

        if locality:
            base_where += """
              AND (neighborhood LIKE ? COLLATE NOCASE
                   OR listing_area LIKE ? COLLATE NOCASE)
            """
            locality_pattern = f"%{locality}%"
            params.extend([locality_pattern, locality_pattern])

        sql = f"""
            SELECT
                restaurant_id, name, city, listing_area, neighborhood,
                cuisines, cuisine_tokens, aggregate_rating, votes,
                cost_for_two, budget_band, rest_type, dish_liked,
                additional_text, source_url
            FROM restaurants
            {base_where}
        """

        count_sql = f"""
            SELECT COUNT(*) FROM restaurants
            {base_where}
        """

        conn = self.connect()
        try:
            total = int(conn.execute(count_sql, params).fetchone()[0])
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
            return rows, total
        finally:
            conn.close()

    def run_sample_queries(self) -> List[Dict[str, Any]]:
        """Run documented sample queries for manual verification."""
        conn = self.connect()
        results: List[Dict[str, Any]] = []
        try:
            results.append(
                {
                    "name": "count_all",
                    "rows": [dict(r) for r in conn.execute(SAMPLE_QUERIES["count_all"]).fetchall()],
                }
            )
            results.append(
                {
                    "name": "by_city",
                    "rows": [dict(r) for r in conn.execute(SAMPLE_QUERIES["by_city"]).fetchall()],
                }
            )
            example_params = ("Bangalore", "medium", 4.0, "%North Indian%")
            results.append(
                {
                    "name": "filter_example",
                    "params": example_params,
                    "rows": [
                        dict(r)
                        for r in conn.execute(
                            SAMPLE_QUERIES["filter_example"], example_params
                        ).fetchall()
                    ],
                }
            )
            return results
        finally:
            conn.close()

    def get_localities(self, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return sorted, deduplicated locality entries for the locations endpoint.

        Pulls from both `neighborhood` (raw `location` column — e.g. "Indiranagar")
        and `listing_area` (raw `listed_in(city)` — e.g. "BTM"), extracting the first
        comma-segment as the actual locality name.

        Args:
            city: Optional canonical metro city name to scope results (e.g. "Bangalore").

        Returns:
            List of dicts: [{city, locality}] sorted by city then locality.
        """
        city_clause = "AND city = ?" if city else ""
        params: tuple = (city,) if city else ()

        neighborhood_sql = f"""
            SELECT DISTINCT
                city,
                TRIM(SUBSTR(neighborhood, 1,
                    CASE WHEN INSTR(neighborhood, ',') > 0
                         THEN INSTR(neighborhood, ',') - 1
                         ELSE LENGTH(neighborhood)
                    END
                )) AS locality
            FROM restaurants
            WHERE neighborhood IS NOT NULL
              AND TRIM(neighborhood) != ''
              AND TRIM(neighborhood) != 'nan'
              {city_clause}
        """

        listing_sql = f"""
            SELECT DISTINCT
                city,
                TRIM(SUBSTR(listing_area, 1,
                    CASE WHEN INSTR(listing_area, ',') > 0
                         THEN INSTR(listing_area, ',') - 1
                         ELSE LENGTH(listing_area)
                    END
                )) AS locality
            FROM restaurants
            WHERE listing_area IS NOT NULL
              AND TRIM(listing_area) != ''
              AND TRIM(listing_area) != 'nan'
              {city_clause}
        """

        conn = self.connect()
        try:
            neighborhood_rows = conn.execute(neighborhood_sql, params).fetchall()
            listing_rows = conn.execute(listing_sql, params).fetchall()
        finally:
            conn.close()

        # Merge, clean and deduplicate
        seen: set = set()
        results: List[Dict[str, Any]] = []

        for row in list(neighborhood_rows) + list(listing_rows):
            raw_city = (row[0] or "").strip()
            raw_locality = (row[1] or "").strip()

            # Skip junk values
            if not raw_locality or raw_locality.lower() in {"nan", "none", "null", "-", "n/a"}:
                continue
            # Skip if locality is just a digit or very short (< 3 chars)
            if len(raw_locality) < 3 or raw_locality.isdigit():
                continue

            key = (raw_city, raw_locality.lower())
            if key in seen:
                continue
            seen.add(key)
            results.append({"city": raw_city, "locality": raw_locality})

        # Sort alphabetically by city then locality
        results.sort(key=lambda x: (x["city"].lower(), x["locality"].lower()))
        return results


