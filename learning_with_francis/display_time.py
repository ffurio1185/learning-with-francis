"""Display SQLite's UTC timestamps in German local time without changing storage."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


BERLIN = ZoneInfo("Europe/Berlin")


def berlin_datetime(value):
    """Interpret offset-free SQLite dates as UTC, then apply Berlin's DST rules."""
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(BERLIN)
