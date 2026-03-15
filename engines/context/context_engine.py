from datetime import datetime


def get_context_score(timestamp=None):
    """
    Returns a genre multiplier based on time of day and day of week.
    1.2  = 20% boost for compatible genres (late night)
    1.15 = 15% boost (weekend)
    1.1  = 10% boost (weekday daytime)
    """
    timestamp  = timestamp or datetime.now()
    hour       = timestamp.hour
    is_weekend = timestamp.weekday() >= 5

    if hour >= 21 or hour < 6:
        return 1.2
    elif is_weekend:
        return 1.15
    else:
        return 1.1