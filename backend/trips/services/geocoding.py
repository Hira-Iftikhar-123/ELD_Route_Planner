from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings


class GeocodingError(Exception):
    pass


@dataclass
class Place:
    label: str
    lat: float
    lon: float


def geocode(query: str) -> Place:
    key = settings.GEOLOCATION_API_KEY
    if not key:
        raise GeocodingError("GEOLOCATION_API_KEY is not configured.")

    response = requests.get(
        "https://api.geoapify.com/v1/geocode/search",
        params={
            "text": query,
            "apiKey": key,
            "limit": 1,
            "format": "json",
        },
        timeout=20,
    )
    if response.status_code != 200:
        raise GeocodingError(f"Geocoding failed ({response.status_code}).")

    results = response.json().get("results") or []
    if not results:
        raise GeocodingError(f"No results for “{query}”.")

    hit = results[0]
    return Place(
        label=_short_label(hit, fallback=query),
        lat=float(hit["lat"]),
        lon=float(hit["lon"]),
    )


def _short_label(hit: dict, *, fallback: str) -> str:
    city = hit.get("city") or hit.get("town") or hit.get("village") or hit.get("county")
    state = hit.get("state_code") or hit.get("state")
    country = str(hit.get("country_code") or hit.get("country") or "").upper()
    if country in ("US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"):
        country = "USA"
    elif len(country) > 3:
        country = country.title()

    if city and state:
        return f"{city}, {state}, {country}" if country else f"{city}, {state}"
    if city and country:
        return f"{city}, {country}"

    label = hit.get("formatted") or hit.get("address_line1") or fallback
    return label.replace("United States of America", "USA").replace("United States", "USA")
