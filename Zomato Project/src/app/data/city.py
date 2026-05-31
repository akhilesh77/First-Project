"""Metro city normalization and aliases (ingest + filter)."""

from __future__ import annotations

from typing import Dict, Optional

CITY_ALIASES: Dict[str, str] = {
    "bengaluru": "Bangalore",
    "bangalore": "Bangalore",
    "banglore": "Bangalore",
    "bengalore": "Bangalore",
    "btm bangalore": "Bangalore",
    "new delhi": "Delhi",
    "delhi": "Delhi",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "chennai": "Chennai",
    "madras": "Chennai",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
}

KNOWN_METROS = set(CITY_ALIASES.values())


def normalize_metro_city(location: Optional[str]) -> Optional[str]:
    """Normalize user or raw location input to a canonical metro name."""
    if not location:
        return None
    key = location.strip().lower()
    if key in CITY_ALIASES:
        return CITY_ALIASES[key]
    titled = location.strip().title()
    if titled in KNOWN_METROS:
        return titled
    return titled
