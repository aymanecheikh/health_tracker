from datetime import datetime
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")

def to_london_date(utc_dt: datetime) -> datetime.date:
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
    local = utc_dt.astimezone(LONDON)
    return local.date()