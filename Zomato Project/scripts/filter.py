"""CLI: run Phase 2 preference filter against SQLite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.filter import PreferenceFilter, UserPreferences  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter restaurants by user preferences (Phase 2).")
    parser.add_argument("--location", required=True, help="City e.g. Bangalore, Bengaluru")
    parser.add_argument("--budget", required=True, choices=["low", "medium", "high"])
    parser.add_argument("--cuisine", required=True, help="Cuisine substring e.g. 'North Indian'")
    parser.add_argument("--min-rating", type=float, required=True)
    parser.add_argument("--additional", default="", help="Optional free-text preferences")
    parser.add_argument("--top", type=int, help="Max candidates (default: N_MAX_CANDIDATES)")
    args = parser.parse_args()

    prefs = UserPreferences(
        location=args.location,
        budget=args.budget,
        cuisine=args.cuisine,
        min_rating=args.min_rating,
        additional_preferences=args.additional or None,
        max_candidates=args.top,
    )

    result = PreferenceFilter().find_candidates(prefs)
    output = {
        "total_matched": result.total_matched,
        "returned": len(result.candidates),
        "truncated": result.truncated,
        "message": result.message,
        "candidates": result.candidates,
    }
    print(json.dumps(output, indent=2, default=str))
    return 0 if result.candidates or result.message else 1


if __name__ == "__main__":
    raise SystemExit(main())
