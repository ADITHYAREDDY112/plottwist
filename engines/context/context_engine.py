from datetime import datetime


LATE_NIGHT_GENRES = ["thriller", "horror", "noir", "crime"]
WEEKEND_GENRES = ["drama", "adventure", "sci fi"]


def get_context_score(timestamp=None):
    """
    Returns a genre multiplier based on time of day and day of week.
    1.2  = 20% boost for compatible genres (late night)
    1.15 = 15% boost (weekend)
    1.0  = neutral weekday baseline
    """
    return get_context_metadata(timestamp)["multiplier"]


def get_context_metadata(timestamp=None, source="server", timezone=None):
    """
    Describe the context rule applied for a recommendation request.
    This is intentionally rule-based; it is not a learned user preference model.
    """
    timestamp = timestamp or datetime.now()
    hour = timestamp.hour
    is_weekend = timestamp.weekday() >= 5

    if hour >= 21 or hour < 6:
        bucket = "late_night"
        multiplier = 1.2
        boost_genres = LATE_NIGHT_GENRES
    elif is_weekend:
        bucket = "weekend"
        multiplier = 1.15
        boost_genres = WEEKEND_GENRES
    else:
        bucket = "weekday"
        multiplier = 1.0
        boost_genres = []

    return {
        "source": source,
        "timestamp": timestamp.isoformat(),
        "timezone": timezone,
        "local_hour": hour,
        "is_weekend": is_weekend,
        "bucket": bucket,
        "multiplier": multiplier,
        "boosted_genres": boost_genres,
        "personalized": False,
    }
