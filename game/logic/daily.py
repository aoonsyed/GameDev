"""Date-seeded daily challenge: the same rings for every player on a UTC day."""

from datetime import date, datetime, timezone


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def daily_key(day: date) -> str:
    return day.isoformat()


def daily_seed(day: date) -> int:
    # Knuth multiplicative mix so neighbouring days get unrelated seeds.
    # (Python's hash() is salted per process, so it can't be used here.)
    x = day.year * 10000 + day.month * 100 + day.day
    return (x * 2654435761) % 2**32
