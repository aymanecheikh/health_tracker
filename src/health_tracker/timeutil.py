from datetime import datetime, date
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")

def to_london_date(utc_dt: datetime) -> date:
    """Convert UTC or naive datetime to Europe/London local date."""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC)
    return utc_dt.astimezone(LONDON).date()
