"""Helpers for converting recipe times to ISO 8601 durations."""


def minutes_to_duration(minutes) -> str | None:
    """Convert a number of minutes to an ISO 8601 duration like 'PT1H30M'."""
    if minutes is None:
        return None
    minutes = int(minutes)
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"PT{hours}H{mins}M"
    if hours:
        return f"PT{hours}H"
    return f"PT{mins}M"
