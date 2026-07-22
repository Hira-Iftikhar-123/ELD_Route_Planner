from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings

from .geocoding import Place


class RoutingError(Exception):
    pass


@dataclass
class RouteLeg:
    distance_miles: float
    duration_hours: float
    geometry: list[list[float]]


@dataclass
class FullRoute:
    distance_miles: float
    duration_hours: float
    geometry: list[list[float]]
    legs: list[RouteLeg]


def _coords(place: Place) -> str:
    return f"{place.lat},{place.lon}"


def route_places(places: list[Place]) -> FullRoute:
    if len(places) < 2:
        raise RoutingError("Need at least two places to route.")

    key = settings.GEOLOCATION_API_KEY
    if not key:
        raise RoutingError("GEOLOCATION_API_KEY is not configured.")

    waypoints = "|".join(_coords(p) for p in places)
    response = requests.get(
        "https://api.geoapify.com/v1/routing",
        params={
            "waypoints": waypoints,
            "mode": "drive",
            "apiKey": key,
        },
        timeout=45,
    )
    if response.status_code != 200:
        raise RoutingError(f"Routing failed ({response.status_code}).")

    payload = response.json()
    if payload.get("error") or payload.get("statusCode"):
        message = payload.get("message") or "Routing request failed."
        raise RoutingError(message)

    features = payload.get("features") or []
    if not features:
        raise RoutingError("No route found between the given locations.")

    feature = features[0]
    props = feature.get("properties") or {}
    distance_m = float(props.get("distance") or 0)
    duration_s = float(props.get("time") or 0)

    geometry = _extract_latlon(feature.get("geometry") or {})
    legs = _build_legs(props.get("legs") or [], geometry, distance_m, duration_s, len(places) - 1)

    return FullRoute(
        distance_miles=distance_m / 1609.344,
        duration_hours=duration_s / 3600.0,
        geometry=geometry,
        legs=legs,
    )


def _extract_latlon(geometry: dict) -> list[list[float]]:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    points: list[list[float]] = []

    def add_line(line: list) -> None:
        for lon, lat, *_rest in line:
            points.append([float(lat), float(lon)])

    if gtype == "LineString":
        add_line(coords)
    elif gtype == "MultiLineString":
        for line in coords:
            add_line(line)
    return _downsample(points, max_points=800)


def _downsample(points: list[list[float]], max_points: int) -> list[list[float]]:
    if len(points) <= max_points:
        return points
    step = max(1, len(points) // max_points)
    sampled = points[::step]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return sampled


def _build_legs(
    raw_legs: list,
    geometry: list[list[float]],
    total_distance_m: float,
    total_duration_s: float,
    expected: int,
) -> list[RouteLeg]:
    if raw_legs:
        out: list[RouteLeg] = []
        for leg in raw_legs:
            dist_m = float(leg.get("distance") or 0)
            dur_s = float(leg.get("time") or 0)
            out.append(
                RouteLeg(
                    distance_miles=dist_m / 1609.344,
                    duration_hours=dur_s / 3600.0,
                    geometry=[],
                )
            )
        if geometry and total_distance_m > 0:
            shares = [leg.distance_miles * 1609.344 / total_distance_m for leg in out]
            out = _split_geometry(out, geometry, shares)
        return out

    n = max(expected, 1)
    share = 1.0 / n
    legs = [
        RouteLeg(
            distance_miles=(total_distance_m / 1609.344) * share,
            duration_hours=(total_duration_s / 3600.0) * share,
            geometry=[],
        )
        for _ in range(n)
    ]
    return _split_geometry(legs, geometry, [share] * n)


def _split_geometry(
    legs: list[RouteLeg],
    geometry: list[list[float]],
    shares: list[float],
) -> list[RouteLeg]:
    if not geometry:
        return legs
    n = len(geometry)
    start = 0
    filled: list[RouteLeg] = []
    acc = 0.0
    for i, leg in enumerate(legs):
        acc += shares[i]
        end = n - 1 if i == len(legs) - 1 else min(n - 1, int(acc * (n - 1)))
        end = max(end, start + 1)
        filled.append(
            RouteLeg(
                distance_miles=leg.distance_miles,
                duration_hours=leg.duration_hours,
                geometry=geometry[start : end + 1],
            )
        )
        start = end
    return filled