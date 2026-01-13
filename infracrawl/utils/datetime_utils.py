from datetime import datetime, timezone
from typing import Optional, Union


def parse_to_utc_naive(value: Union[str, datetime, None]) -> Optional[datetime]:
    """Parse an ISO datetime string or datetime object and return a UTC-naive datetime.

    Returns None if parsing fails or value is None.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        # assume string
        try:
            dt = datetime.fromisoformat(value)
        except Exception:
            import logging
            logging.debug("Could not parse datetime string: %s", value)
            return None
    try:
        if dt.tzinfo is not None:
            dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            dt_utc = dt
        return dt_utc
    except Exception:
        import logging
        logging.exception("Error converting datetime to UTC: %s", dt)
        return None
