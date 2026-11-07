"""Business days and local times for the feed's calendar.

Why a module of its own:
    The SLA says "the file for business date D lands by 06:00 CT on the next business day".
    That sentence needs three things: which days are business days, what "next" means after a
    Friday, and what 06:00 in Chicago is in UTC, which changes when daylight saving time ends
    (on 2026-11-01 Chicago moves from UTC-5 to UTC-6). Getting any of them wrong moves every
    deadline, so they live in one tested place. Level 3 builds the SLA clock on top of this.

Scope: Monday to Friday. Holidays are out of scope for the demo (see docs/spec.md).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# Monday is 0 ... Friday is 4 (Python's weekday numbering)
LAST_WEEKDAY = 4


def is_business_day(day: date) -> bool:
    """True from Monday to Friday."""
    return day.weekday() <= LAST_WEEKDAY


def next_business_day(day: date) -> date:
    """The first business day after `day` (a Friday's next business day is the Monday).

    Args:
        day: Any date.

    Returns:
        The next Monday-to-Friday date.
    """
    # Step forward one calendar day at a time until a weekday is reached
    candidate = day + timedelta(days=1)
    while not is_business_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def business_dates(first: date, count: int) -> list[date]:
    """The first `count` business dates starting at `first` (inclusive when it is a business day).

    Args:
        first: Where the calendar starts.
        count: How many business dates to return.

    Returns:
        The business dates, in order.
    """
    # Start on `first` itself if it is a business day, otherwise on the next one
    day = first if is_business_day(first) else next_business_day(first)
    dates = [day]
    # Keep adding the next business day until the list is long enough
    while len(dates) < count:
        day = next_business_day(day)
        dates.append(day)
    return dates


def parse_local_time(text: str) -> time:
    """Read an "HH:MM" setting such as "06:00" into a time of day."""
    hours, minutes = text.split(":")
    return time(int(hours), int(minutes))


def local_datetime(day: date, local_time: str, timezone: str) -> datetime:
    """A wall-clock time on a given day in a given time zone, as an aware datetime.

    Why aware datetimes: "06:00 in Chicago" is 11:00 UTC in October and 12:00 UTC in November.
    An aware datetime carries its zone, so comparing it with a UTC arrival time is always right.

    Args:
        day: The calendar date.
        local_time: "HH:MM", wall-clock time in that zone.
        timezone: IANA zone name, e.g. "America/Chicago".

    Returns:
        The aware datetime.
    """
    return datetime.combine(day, parse_local_time(local_time), tzinfo=ZoneInfo(timezone))


def deadline_for(business_date: date, local_time: str, timezone: str) -> datetime:
    """When the file for `business_date` is due: `local_time` on the next business day.

    Args:
        business_date: The date the file covers (D).
        local_time: The deadline's wall-clock time, e.g. "06:00".
        timezone: IANA zone of the deadline.

    Returns:
        The deadline as an aware datetime in that zone.
    """
    return local_datetime(next_business_day(business_date), local_time, timezone)
