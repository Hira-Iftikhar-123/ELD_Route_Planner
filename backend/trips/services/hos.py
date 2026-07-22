from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

Status = Literal["off_duty", "sleeper", "driving", "on_duty"]

MAX_DRIVE_HOURS = 11.0
MAX_WINDOW_HOURS = 14.0
BREAK_AFTER_DRIVE_HOURS = 8.0
BREAK_MINUTES = 30
RESET_OFF_HOURS = 10.0
RESTART_34_HOURS = 34.0
CYCLE_LIMIT_HOURS = 70.0
FUEL_EVERY_MILES = 1000.0
FUEL_STOP_HOURS = 0.5
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0
MIN_SLICE_HOURS = 1 / 60

HOME_TZ = ZoneInfo("America/Chicago")


@dataclass
class Segment:
    status: Status
    start: datetime
    end: datetime
    location: str
    remark: str = ""
    miles: float = 0.0

    @property
    def hours(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds() / 3600.0)


@dataclass
class StopEvent:
    type: str
    label: str
    lat: float
    lon: float
    arrival: datetime
    duration_hours: float
    remark: str


@dataclass
class DayLog:
    date: str
    from_location: str
    to_location: str
    total_miles: float
    segments: list[dict]
    totals: dict[str, float]
    remarks: list[str]
    recap: dict[str, float]


@dataclass
class PlannerResult:
    summary: dict
    stops: list[dict]
    route: dict
    daily_logs: list[DayLog]
    segments: list[dict]


@dataclass
class _ShiftState:
    now: datetime
    cycle_used: float
    drive_used: float = 0.0
    drive_since_break: float = 0.0
    window_start: datetime | None = None
    miles_since_fuel: float = 0.0
    segments: list[Segment] = field(default_factory=list)
    stops: list[StopEvent] = field(default_factory=list)


def plan_hos_trip(
    *,
    current_label: str,
    pickup_label: str,
    dropoff_label: str,
    current_lat: float,
    current_lon: float,
    pickup_lat: float,
    pickup_lon: float,
    dropoff_lat: float,
    dropoff_lon: float,
    cycle_used_hours: float,
    leg_to_pickup_miles: float,
    leg_to_pickup_hours: float,
    leg_to_dropoff_miles: float,
    leg_to_dropoff_hours: float,
    route_geometry: list[list[float]],
    start_at: datetime | None = None,
) -> PlannerResult:
    start = start_at or _default_start()
    state = _ShiftState(now=start, cycle_used=max(0.0, min(cycle_used_hours, CYCLE_LIMIT_HOURS)))

    _drive_leg(
        state,
        miles=leg_to_pickup_miles,
        hours=leg_to_pickup_hours,
        from_label=current_label,
        to_label=pickup_label,
        to_lat=pickup_lat,
        to_lon=pickup_lon,
        purpose="Travel to pickup",
    )
    _on_duty_stop(
        state,
        hours=PICKUP_HOURS,
        label=pickup_label,
        lat=pickup_lat,
        lon=pickup_lon,
        stop_type="pickup",
        remark=f"Pickup — {PICKUP_HOURS:.0f} hr on-duty at {pickup_label}",
    )

    _drive_leg(
        state,
        miles=leg_to_dropoff_miles,
        hours=leg_to_dropoff_hours,
        from_label=pickup_label,
        to_label=dropoff_label,
        to_lat=dropoff_lat,
        to_lon=dropoff_lon,
        purpose="Haul to dropoff",
    )
    _on_duty_stop(
        state,
        hours=DROPOFF_HOURS,
        label=dropoff_label,
        lat=dropoff_lat,
        lon=dropoff_lon,
        stop_type="dropoff",
        remark=f"Dropoff — {DROPOFF_HOURS:.0f} hr on-duty at {dropoff_label}",
    )

    _pad_final_off_duty(state)

    daily_logs = _apply_recap(
        state.segments,
        cycle_used_hours,
        origin_label=current_label,
        destination_label=dropoff_label,
    )
    total_miles = leg_to_pickup_miles + leg_to_dropoff_miles
    summary = {
        "total_miles": round(total_miles, 1),
        "total_drive_hours": round(_status_hours(state.segments, "driving"), 2),
        "total_on_duty_hours": round(_on_duty_hours(state.segments), 2),
        "days": len(daily_logs),
        "cycle_used_start": round(cycle_used_hours, 2),
        "cycle_used_end": round(
            _cycle_after_segments(state.segments, cycle_used_hours),
            2,
        ),
        "assumptions": {
            "rule_set": "70_hour_8_day",
            "pickup_hours": PICKUP_HOURS,
            "dropoff_hours": DROPOFF_HOURS,
            "fuel_every_miles": FUEL_EVERY_MILES,
            "adverse_conditions": False,
        },
    }

    return PlannerResult(
        summary=summary,
        stops=[_stop_dict(s) for s in state.stops],
        route={
            "distance_miles": round(total_miles, 1),
            "geometry": route_geometry,
            "waypoints": [
                {"type": "current", "label": current_label, "lat": current_lat, "lon": current_lon},
                {"type": "pickup", "label": pickup_label, "lat": pickup_lat, "lon": pickup_lon},
                {"type": "dropoff", "label": dropoff_label, "lat": dropoff_lat, "lon": dropoff_lon},
            ],
        },
        daily_logs=daily_logs,
        segments=[_segment_dict(s) for s in state.segments],
    )


def _default_start() -> datetime:
    now = datetime.now(HOME_TZ)
    start = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now.hour >= 18:
        start += timedelta(days=1)
    return start


def _drive_leg(
    state: _ShiftState,
    *,
    miles: float,
    hours: float,
    from_label: str,
    to_label: str,
    to_lat: float,
    to_lon: float,
    purpose: str,
) -> None:
    if miles <= 0 or hours <= 0:
        return

    remaining_miles = miles
    remaining_hours = hours
    speed = miles / hours

    while remaining_hours > MIN_SLICE_HOURS:
        _ensure_can_drive(state)

        miles_room = FUEL_EVERY_MILES - state.miles_since_fuel
        if miles_room <= 0:
            _fuel_stop(state, label=from_label if remaining_miles == miles else f"Fuel near {to_label}")
            continue

        drive_room = min(
            MAX_DRIVE_HOURS - state.drive_used,
            BREAK_AFTER_DRIVE_HOURS - state.drive_since_break,
            _window_remaining(state),
            CYCLE_LIMIT_HOURS - state.cycle_used,
            remaining_hours,
            miles_room / speed if speed > 0 else remaining_hours,
        )

        if drive_room <= MIN_SLICE_HOURS:
            if state.drive_since_break >= BREAK_AFTER_DRIVE_HOURS - 1e-6:
                _rest_break(state, label=f"30-min break en route to {to_label}")
                continue
            if state.drive_used >= MAX_DRIVE_HOURS - 1e-6 or _window_remaining(state) <= MIN_SLICE_HOURS:
                _ten_hour_reset(state, label=f"10-hr reset before continuing to {to_label}")
                continue
            if state.cycle_used >= CYCLE_LIMIT_HOURS - 1e-6:
                _thirty_four_restart(state, label="34-hr restart — weekly cycle exhausted")
                continue
            _ten_hour_reset(state, label=f"10-hr reset before continuing to {to_label}")
            continue

        slice_hours = drive_room
        slice_miles = min(remaining_miles, slice_hours * speed)
        slice_hours = slice_miles / speed if speed > 0 else slice_hours

        loc = to_label if remaining_miles - slice_miles <= 0.5 else f"En route to {to_label}"
        remark = purpose if remaining_miles - slice_miles <= 0.5 else f"{purpose} (partial)"
        _add_segment(
            state,
            status="driving",
            hours=slice_hours,
            location=loc,
            remark=remark,
            miles=slice_miles,
            counts_drive=True,
            counts_cycle=True,
        )
        state.miles_since_fuel += slice_miles
        remaining_miles -= slice_miles
        remaining_hours -= slice_hours

        if state.miles_since_fuel >= FUEL_EVERY_MILES - 1e-6 and remaining_hours > MIN_SLICE_HOURS:
            _fuel_stop(state, label=f"Fuel stop en route to {to_label}")

    state.stops.append(
        StopEvent(
            type="arrival",
            label=to_label,
            lat=to_lat,
            lon=to_lon,
            arrival=state.now,
            duration_hours=0.0,
            remark=f"Arrived {to_label}",
        )
    )


def _ensure_can_drive(state: _ShiftState) -> None:
    if state.window_start is None:
        return
    if state.cycle_used >= CYCLE_LIMIT_HOURS - 1e-6:
        _thirty_four_restart(state, label="34-hr restart — weekly cycle exhausted")
    elif state.drive_used >= MAX_DRIVE_HOURS - 1e-6 or _window_remaining(state) <= MIN_SLICE_HOURS:
        _ten_hour_reset(state, label="10-hr off-duty reset")
    elif state.drive_since_break >= BREAK_AFTER_DRIVE_HOURS - 1e-6:
        _rest_break(state, label="30-min break from driving")


def _window_remaining(state: _ShiftState) -> float:
    if state.window_start is None:
        return MAX_WINDOW_HOURS
    elapsed = (state.now - state.window_start).total_seconds() / 3600.0
    return max(0.0, MAX_WINDOW_HOURS - elapsed)


def _on_duty_stop(
    state: _ShiftState,
    *,
    hours: float,
    label: str,
    lat: float,
    lon: float,
    stop_type: str,
    remark: str,
) -> None:
    remaining = hours
    while remaining > MIN_SLICE_HOURS:
        if state.window_start is None:
            state.window_start = state.now

        room = min(
            _window_remaining(state),
            CYCLE_LIMIT_HOURS - state.cycle_used,
            remaining,
        )
        if room <= MIN_SLICE_HOURS:
            if state.cycle_used >= CYCLE_LIMIT_HOURS - 1e-6:
                _thirty_four_restart(state, label="34-hr restart before on-duty work")
            else:
                _ten_hour_reset(state, label="10-hr reset before on-duty work")
            continue

        chunk = room
        start = state.now
        _add_segment(
            state,
            status="on_duty",
            hours=chunk,
            location=label,
            remark=remark,
            miles=0.0,
            counts_drive=False,
            counts_cycle=True,
        )
        remaining -= chunk
        if remaining <= MIN_SLICE_HOURS:
            state.stops.append(
                StopEvent(
                    type=stop_type,
                    label=label,
                    lat=lat,
                    lon=lon,
                    arrival=start,
                    duration_hours=hours,
                    remark=remark,
                )
            )


def _fuel_stop(state: _ShiftState, *, label: str) -> None:
    remark = f"Fueling (~{FUEL_STOP_HOURS * 60:.0f} min) — {label}"
    start = state.now
    _add_segment(
        state,
        status="on_duty",
        hours=FUEL_STOP_HOURS,
        location=label,
        remark=remark,
        miles=0.0,
        counts_drive=False,
        counts_cycle=True,
        resets_break=True,
    )
    state.miles_since_fuel = 0.0
    state.stops.append(
        StopEvent(
            type="fuel",
            label=label,
            lat=0.0,
            lon=0.0,
            arrival=start,
            duration_hours=FUEL_STOP_HOURS,
            remark=remark,
        )
    )


def _rest_break(state: _ShiftState, *, label: str) -> None:
    hours = BREAK_MINUTES / 60.0
    remark = f"30-minute break from driving — {label}"
    start = state.now
    _add_segment(
        state,
        status="off_duty",
        hours=hours,
        location=label,
        remark=remark,
        miles=0.0,
        counts_drive=False,
        counts_cycle=False,
        resets_break=True,
    )
    state.stops.append(
        StopEvent(
            type="break_30",
            label=label,
            lat=0.0,
            lon=0.0,
            arrival=start,
            duration_hours=hours,
            remark=remark,
        )
    )


def _ten_hour_reset(state: _ShiftState, *, label: str) -> None:
    remark = f"10 consecutive hours off duty — {label}"
    start = state.now
    _add_segment(
        state,
        status="sleeper",
        hours=RESET_OFF_HOURS,
        location=label,
        remark=remark,
        miles=0.0,
        counts_drive=False,
        counts_cycle=False,
        resets_break=True,
        resets_shift=True,
    )
    state.stops.append(
        StopEvent(
            type="rest_10",
            label=label,
            lat=0.0,
            lon=0.0,
            arrival=start,
            duration_hours=RESET_OFF_HOURS,
            remark=remark,
        )
    )


def _thirty_four_restart(state: _ShiftState, *, label: str) -> None:
    remark = f"34-hour restart — {label}"
    start = state.now
    _add_segment(
        state,
        status="off_duty",
        hours=RESTART_34_HOURS,
        location=label,
        remark=remark,
        miles=0.0,
        counts_drive=False,
        counts_cycle=False,
        resets_break=True,
        resets_shift=True,
        resets_cycle=True,
    )
    state.stops.append(
        StopEvent(
            type="restart_34",
            label=label,
            lat=0.0,
            lon=0.0,
            arrival=start,
            duration_hours=RESTART_34_HOURS,
            remark=remark,
        )
    )


def _add_segment(
    state: _ShiftState,
    *,
    status: Status,
    hours: float,
    location: str,
    remark: str,
    miles: float,
    counts_drive: bool,
    counts_cycle: bool,
    resets_break: bool = False,
    resets_shift: bool = False,
    resets_cycle: bool = False,
) -> None:
    if hours <= 0:
        return

    if state.window_start is None and status in ("driving", "on_duty"):
        state.window_start = state.now

    start = state.now
    end = start + timedelta(hours=hours)
    state.segments.append(
        Segment(status=status, start=start, end=end, location=location, remark=remark, miles=miles)
    )
    state.now = end

    if counts_drive:
        state.drive_used += hours
        state.drive_since_break += hours
    if counts_cycle:
        state.cycle_used += hours
    if resets_break:
        state.drive_since_break = 0.0
    if resets_shift:
        state.drive_used = 0.0
        state.drive_since_break = 0.0
        state.window_start = None
    if resets_cycle:
        state.cycle_used = 0.0


def _pad_final_off_duty(state: _ShiftState) -> None:
    if not state.segments:
        return
    local = state.now.astimezone(HOME_TZ)
    midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    hours = (midnight - local).total_seconds() / 3600.0
    if hours > MIN_SLICE_HOURS:
        _add_segment(
            state,
            status="off_duty",
            hours=hours,
            location=state.segments[-1].location,
            remark="Off duty after trip complete",
            miles=0.0,
            counts_drive=False,
            counts_cycle=False,
        )


def _status_hours(segments: list[Segment], status: Status) -> float:
    return sum(s.hours for s in segments if s.status == status)


def _on_duty_hours(segments: list[Segment]) -> float:
    return sum(s.hours for s in segments if s.status in ("driving", "on_duty"))


def _cycle_after_segments(segments: list[Segment], start_cycle: float) -> float:
    used = start_cycle
    for s in segments:
        if "34-hour restart" in (s.remark or ""):
            used = 0.0
            continue
        if s.status in ("driving", "on_duty"):
            used += s.hours
    return used


def _segment_dict(s: Segment) -> dict:
    return {
        "status": s.status,
        "start": s.start.isoformat(),
        "end": s.end.isoformat(),
        "hours": round(s.hours, 3),
        "location": s.location,
        "remark": s.remark,
        "miles": round(s.miles, 2),
    }


def _stop_dict(s: StopEvent) -> dict:
    return {
        "type": s.type,
        "label": s.label,
        "lat": s.lat,
        "lon": s.lon,
        "arrival": s.arrival.isoformat(),
        "duration_hours": round(s.duration_hours, 3),
        "remark": s.remark,
    }


def _apply_recap(
    segments: list[Segment],
    cycle_used_start: float,
    *,
    origin_label: str,
    destination_label: str,
) -> list[DayLog]:
    if not segments:
        return []

    by_day: dict[date, list[Segment]] = {}
    for seg in segments:
        pieces = _split_segment_at_midnights(seg)
        for piece in pieces:
            day = piece.start.astimezone(HOME_TZ).date()
            by_day.setdefault(day, []).append(piece)

    logs: list[DayLog] = []
    running_cycle = cycle_used_start
    day_keys = sorted(by_day.keys())

    for index, day in enumerate(day_keys):
        day_segs = _ensure_full_day(day, by_day[day])
        totals = {
            "off_duty": round(sum(s.hours for s in day_segs if s.status == "off_duty"), 2),
            "sleeper": round(sum(s.hours for s in day_segs if s.status == "sleeper"), 2),
            "driving": round(sum(s.hours for s in day_segs if s.status == "driving"), 2),
            "on_duty": round(sum(s.hours for s in day_segs if s.status == "on_duty"), 2),
        }
        total_logged = sum(totals.values())
        if abs(total_logged - 24.0) < 0.2:
            totals["off_duty"] = round(totals["off_duty"] + (24.0 - total_logged), 2)

        on_duty_today = totals["driving"] + totals["on_duty"]
        for s in day_segs:
            if "34-hour restart" in (s.remark or ""):
                running_cycle = 0.0
        running_cycle += on_duty_today
        available_tomorrow = max(0.0, CYCLE_LIMIT_HOURS - running_cycle)

        miles = round(sum(s.miles for s in day_segs), 1)
        remarks = []
        for s in day_segs:
            if s.remark and s.status != "driving":
                remarks.append(
                    f"{s.start.astimezone(HOME_TZ).strftime('%H:%M')} {s.remark}"
                )
            elif s.remark and s.miles > 0 and "partial" not in s.remark.lower():
                remarks.append(
                    f"{s.start.astimezone(HOME_TZ).strftime('%H:%M')} {s.remark}"
                )

        active = [s for s in day_segs if s.status in ("driving", "on_duty")]
        from_loc = origin_label if index == 0 else (active[0].location if active else day_segs[0].location)
        if index == len(day_keys) - 1:
            to_loc = destination_label
        else:
            to_loc = active[-1].location if active else day_segs[-1].location

        logs.append(
            DayLog(
                date=day.isoformat(),
                from_location=from_loc,
                to_location=to_loc,
                total_miles=miles,
                segments=[_segment_dict(s) for s in day_segs],
                totals=totals,
                remarks=remarks,
                recap={
                    "on_duty_today": round(on_duty_today, 2),
                    "total_hours_on_duty_last_8_days": round(running_cycle, 2),
                    "hours_available_tomorrow": round(available_tomorrow, 2),
                    "cycle_used_end_of_day": round(running_cycle, 2),
                },
            )
        )
    return logs


def _ensure_full_day(day: date, segments: list[Segment]) -> list[Segment]:
    if not segments:
        return segments
    start_bound = datetime(day.year, day.month, day.day, tzinfo=HOME_TZ)
    end_bound = start_bound + timedelta(days=1)
    out = list(segments)
    first = out[0]
    if first.start > start_bound + timedelta(seconds=1):
        out.insert(
            0,
            Segment(
                status="off_duty",
                start=start_bound,
                end=first.start,
                location=first.location,
                remark="Off duty before duty status begins",
            ),
        )
    last = out[-1]
    if last.end < end_bound - timedelta(seconds=1):
        out.append(
            Segment(
                status="off_duty",
                start=last.end,
                end=end_bound,
                location=last.location,
                remark="Off duty",
            )
        )
    return out


def _split_segment_at_midnights(seg: Segment) -> list[Segment]:
    pieces: list[Segment] = []
    cursor = seg.start
    while cursor < seg.end - timedelta(seconds=1):
        local = cursor.astimezone(HOME_TZ)
        next_midnight = (local + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cut = min(seg.end, next_midnight)
        ratio = (cut - cursor).total_seconds() / max((seg.end - seg.start).total_seconds(), 1)
        pieces.append(
            Segment(
                status=seg.status,
                start=cursor,
                end=cut,
                location=seg.location,
                remark=seg.remark,
                miles=seg.miles * ratio,
            )
        )
        cursor = cut
    return pieces


def result_to_dict(result: PlannerResult) -> dict:
    return {
        "summary": result.summary,
        "stops": result.stops,
        "route": result.route,
        "daily_logs": [asdict(d) for d in result.daily_logs],
        "segments": result.segments,
    }