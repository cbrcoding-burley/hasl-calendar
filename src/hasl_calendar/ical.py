import re
from datetime import datetime, timedelta, timezone

from icalendar import Calendar, Event, vText

PRODID = "-//HASL Calendar//EN"

# Maps the park portion of a location string to a street address.
_PARK_ADDRESSES = {
    "FRANK SINATRA PARK": "398 Sinatra Dr, Hoboken, NJ 07030",
    "1600 PARK": "1600 Park Ave, Hoboken, NJ 07030",
    "RESILIENCY PARK": "1201 Madison St, Hoboken, NJ 07030",
}

# Separators used in location strings: "PARK - NORTH" or "PARK NORTH"
_LOCATION_RE = re.compile(r"^(.+?)\s*[-–]\s*(\w+)$|^(.+?)\s+(\w+)$")


def _resolve_location(raw: str) -> tuple[str, str]:
    """Split a raw location like 'FRANK SINATRA PARK - NORTH' into
    (street_address, field_label). Falls back to (title-cased raw, '') if unknown."""
    raw = raw.strip().upper()
    for park_key, address in _PARK_ADDRESSES.items():
        if raw.startswith(park_key):
            remainder = raw[len(park_key) :].strip(" -–").strip()
            return address, remainder.title() if remainder else ""
    return raw.title(), ""


def build_feed(team, games) -> bytes:
    """Return a UTF-8 encoded .ics bytes object for the given team and their games."""
    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("x-wr-calname", vText(f"{team.name} – HASL"))
    cal.add("x-wr-timezone", vText("America/New_York"))
    cal.add("x-published-ttl", "PT1H")
    cal.add("refresh-interval;value=duration", "PT1H")

    for game in games:
        evt = Event()
        evt.add("uid", vText(f"{game.id}@hasl-calendar"))

        start = datetime.fromisoformat(game.datetime_local).replace(tzinfo=_eastern())
        end = start + timedelta(hours=1)

        address, field = _resolve_location(game.location)
        description_parts = [game.league]
        if field:
            description_parts.append(f"Field: {field}")

        evt.add("dtstart", start)
        evt.add("dtend", end)
        evt.add("summary", vText(f"{game.home_team.name} vs {game.away_team.name}"))
        evt.add("location", vText(address))
        evt.add("description", vText("\n".join(description_parts)))
        evt.add("last-modified", datetime.now(tz=timezone.utc))

        cal.add_component(evt)

    return cal.to_ical()


def _eastern():
    import zoneinfo

    return zoneinfo.ZoneInfo("America/New_York")
