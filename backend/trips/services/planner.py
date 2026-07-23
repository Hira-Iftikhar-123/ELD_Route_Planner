from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from .geocoding import GeocodingError, Place, geocode
from .hos import plan_hos_trip, result_to_dict
from .routing import FullRoute, RoutingError, route_places


class TripPlannerError(Exception):
    pass


def plan_trip(
    *,
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
    cycle_used_hours: float,
) -> dict:
    try:
        current, pickup, dropoff = _geocode_many(
            [current_location, pickup_location, dropoff_location]
        )
    except GeocodingError as exc:
        raise TripPlannerError(str(exc)) from exc

    if _same_place(pickup, dropoff):
        raise TripPlannerError("Pickup and dropoff must be different locations.")

    try:
        routed: FullRoute = route_places([current, pickup, dropoff])
    except RoutingError as exc:
        raise TripPlannerError(str(exc)) from exc

    if len(routed.legs) < 2:
        raise TripPlannerError("Could not split route into pickup and dropoff legs.")

    leg_pickup, leg_dropoff = routed.legs[0], routed.legs[1]
    result = plan_hos_trip(
        current_label=current.label,
        pickup_label=pickup.label,
        dropoff_label=dropoff.label,
        current_lat=current.lat,
        current_lon=current.lon,
        pickup_lat=pickup.lat,
        pickup_lon=pickup.lon,
        dropoff_lat=dropoff.lat,
        dropoff_lon=dropoff.lon,
        cycle_used_hours=cycle_used_hours,
        leg_to_pickup_miles=leg_pickup.distance_miles,
        leg_to_pickup_hours=leg_pickup.duration_hours,
        leg_to_dropoff_miles=leg_dropoff.distance_miles,
        leg_to_dropoff_hours=leg_dropoff.duration_hours,
        route_geometry=routed.geometry,
    )
    payload = result_to_dict(result)
    _snap_stops_to_route(payload["stops"], payload["segments"], routed.geometry)
    payload["locations"] = {
        "current": _place_dict(current),
        "pickup": _place_dict(pickup),
        "dropoff": _place_dict(dropoff),
    }
    return payload


def _geocode_many(queries: list[str]) -> list[Place]:
    results: list[Place | None] = [None] * len(queries)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(geocode, q): i for i, q in enumerate(queries)}
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
    return [p for p in results if p is not None]


def _place_dict(place: Place) -> dict:
    return {"label": place.label, "lat": place.lat, "lon": place.lon}


def _same_place(a: Place, b: Place) -> bool:
    if a.label.casefold() == b.label.casefold():
        return True
    return abs(a.lat - b.lat) < 0.05 and abs(a.lon - b.lon) < 0.05


def _snap_stops_to_route(
    stops: list[dict],
    segments: list[dict],
    geometry: list[list[float]],
) -> None:
    if not geometry:
        return

    total_drive = sum(float(s.get("miles") or 0) for s in segments if s.get("status") == "driving")
    driven = 0.0
    seg_i = 0

    for stop in stops:
        while seg_i < len(segments):
            seg = segments[seg_i]
            seg_i += 1
            if seg.get("status") == "driving":
                driven += float(seg.get("miles") or 0)
            if (stop.get("remark") or "") == (seg.get("remark") or ""):
                break

        lat, lon = float(stop.get("lat") or 0), float(stop.get("lon") or 0)
        if abs(lat) > 0.01 or abs(lon) > 0.01:
            continue
        if stop.get("type") not in ("fuel", "break_30", "rest_10", "restart_34"):
            continue

        ratio = 0.0 if total_drive <= 0 else min(1.0, driven / total_drive)
        idx = min(len(geometry) - 1, int(ratio * (len(geometry) - 1)))
        point = geometry[idx]
        stop["lat"], stop["lon"] = float(point[0]), float(point[1])