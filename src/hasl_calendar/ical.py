from datetime import datetime, timedelta, timezone

from icalendar import Calendar, Event, vText

PRODID = "-//HASL Calendar//EN"


def build_feed(team, games) -> bytes:
    """Return a UTF-8 encoded .ics bytes object for the given team and their games."""
    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("x-wr-calname", vText(f"{team.name} – HASL"))
    cal.add("x-wr-timezone", vText("America/New_York"))
    # Hint to clients: re-fetch every hour
    cal.add("x-published-ttl", "PT1H")
    cal.add("refresh-interval;value=duration", "PT1H")

    for game in games:
        evt = Event()
        evt.add("uid", vText(f"{game.id}@hasl-calendar"))

        start = datetime.fromisoformat(game.datetime_local).replace(
            tzinfo=_eastern()
        )
        end = start + timedelta(hours=1)

        evt.add("dtstart", start)
        evt.add("dtend", end)
        evt.add("summary", vText(f"{game.home_team.name} vs {game.away_team.name}"))
        evt.add("location", vText(game.location.title()))
        evt.add("description", vText(game.league))
        evt.add("last-modified", datetime.now(tz=timezone.utc))

        cal.add_component(evt)

    return cal.to_ical()


def _eastern():
    """Return a fixed UTC-4 offset (Eastern Daylight Time) as a simple tzinfo.

    The icalendar library handles TZID on DTSTART separately; this offset is used
    so datetime objects are timezone-aware when added to the event.
    """
    # EDT (UTC-4) covers the bulk of the HASL season (through Nov 1 DST change).
    # For correctness across the Nov 1 DST boundary, swap to zoneinfo when deploying.
    import zoneinfo
    return zoneinfo.ZoneInfo("America/New_York")
