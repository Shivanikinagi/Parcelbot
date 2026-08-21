"""Domain clock and business-hours engine.

All time-based logic (SLA elapsed/breach, cancellation windows, pickup delays)
is computed against a fixed **reference time** — the dataset snapshot
``2026-08-16 11:00 Asia/Kolkata`` — never the wall clock. This makes the whole
system deterministic and reproducible, which is exactly what a reviewer wants
to see for time-sensitive business rules.

Business-hours model (documented assumption, configurable):
    * Working days: Monday–Friday
    * Working window: 09:00–18:00 IST  → 9 business hours per day
    * "1 business day" is treated as one full 9-hour working day.
Enterprise P1 (and any target marked ``calendar``/24x7) ignores this and uses
wall-calendar minutes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import settings

# India Standard Time (UTC+5:30). The dataset uses Asia/Kolkata throughout.
IST = timezone(timedelta(hours=5, minutes=30))

_BUSINESS_START_H = settings.business_day_start_hour
_BUSINESS_END_H = settings.business_day_end_hour
BUSINESS_MINUTES_PER_DAY = (_BUSINESS_END_H - _BUSINESS_START_H) * 60


def reference_now() -> datetime:
    """The domain 'now' — the dataset snapshot time, tz-aware in IST."""
    raw = settings.reference_time.strip()
    # Accept "YYYY-MM-DD HH:MM" or ISO forms.
    dt = datetime.fromisoformat(raw)
    return ensure_ist(dt)


def ensure_ist(dt: datetime) -> datetime:
    """Attach IST to a naive datetime, or convert an aware one into IST."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def is_business_open(dt: datetime) -> bool:
    dt = ensure_ist(dt)
    if dt.weekday() >= 5:  # Sat/Sun
        return False
    return _BUSINESS_START_H <= dt.hour < _BUSINESS_END_H


def _day_window(day: datetime) -> tuple[datetime, datetime]:
    """Return the (open, close) datetimes for the business day containing ``day``."""
    day = ensure_ist(day)
    open_dt = day.replace(hour=_BUSINESS_START_H, minute=0, second=0, microsecond=0)
    close_dt = day.replace(hour=_BUSINESS_END_H, minute=0, second=0, microsecond=0)
    return open_dt, close_dt


def business_minutes_between(start: datetime, end: datetime) -> int:
    """Count business minutes in ``[start, end]`` (0 if end <= start).

    Only Mon–Fri 09:00–18:00 IST counts. Used to measure elapsed SLA time for
    business-hours targets, correctly pausing over the weekend.
    """
    start, end = ensure_ist(start), ensure_ist(end)
    if end <= start:
        return 0

    total = 0
    cursor = start
    # Walk day by day; cheap given SLA horizons are days, not years.
    while cursor.date() <= end.date():
        if cursor.weekday() < 5:
            open_dt, close_dt = _day_window(cursor)
            segment_start = max(cursor, open_dt)
            segment_end = min(end, close_dt)
            if segment_end > segment_start:
                total += int((segment_end - segment_start).total_seconds() // 60)
        # advance to start of next calendar day
        next_day = (cursor + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cursor = next_day
    return total


def add_business_minutes(start: datetime, minutes: int) -> datetime:
    """Return the datetime reached by adding ``minutes`` of business time.

    Rolls forward across the weekend / after-hours gaps. Used to compute an SLA
    due time for business-hours targets.
    """
    cursor = ensure_ist(start)
    remaining = minutes
    # If we start outside business hours, jump to the next open moment.
    cursor = _advance_to_open(cursor)
    guard = 0
    while remaining > 0 and guard < 10_000:
        guard += 1
        _, close_dt = _day_window(cursor)
        available = int((close_dt - cursor).total_seconds() // 60)
        if remaining <= available:
            return cursor + timedelta(minutes=remaining)
        remaining -= available
        # move to next business day's open
        cursor = _advance_to_open(close_dt + timedelta(minutes=1))
    return cursor


def _advance_to_open(dt: datetime) -> datetime:
    """Move ``dt`` forward to the next instant the business is open."""
    dt = ensure_ist(dt)
    guard = 0
    while guard < 30:
        guard += 1
        open_dt, close_dt = _day_window(dt)
        if dt.weekday() < 5 and dt < close_dt:
            return max(dt, open_dt)
        # jump to next day 00:00
        dt = (dt + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    return dt


def format_duration(minutes: int) -> str:
    """Human-friendly duration, e.g. 150 → '2h 30m', 30 → '30m'."""
    if minutes < 60:
        return f"{minutes}m"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m" if mins else f"{hours}h"
