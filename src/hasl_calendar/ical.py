import re
from datetime import datetime, timedelta, timezone

from icalendar import Calendar, Event, vText

PRODID = "-//HASL Calendar//EN"
HASL_SCHEDULE_BASE = "https://www.allprosoftware.net/HASLSUMMER23/aplsteam"

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
    (location_string, field_label). location_string is 'Park Name, street address'.
    Falls back to (title-cased raw, '') if unknown."""
    raw = raw.strip().upper()
    for park_key, address in _PARK_ADDRESSES.items():
        if raw.startswith(park_key):
            remainder = raw[len(park_key) :].strip(" -–").strip()
            return f"{park_key.title()}, {address}", (
                remainder.title() if remainder else ""
            )
    return raw.title(), ""


def _location_name(raw: str) -> str:
    """Return the park name without direction, e.g. 'Frank Sinatra Park' from
    'FRANK SINATRA PARK - NORTH'."""
    raw = raw.strip().upper()
    for park_key in _PARK_ADDRESSES:
        if raw.startswith(park_key):
            return park_key.title()
    return raw.title()


def build_feed(team, games) -> bytes:
    """Return a UTF-8 encoded .ics bytes object for the given team and their games."""
    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("x-wr-calname", vText(f"{team.name} – HASL"))
    cal.add("x-wr-timezone", vText("America/New_York"))
    cal.add("x-published-ttl", "PT1H")
    cal.add("refresh-interval;value=duration", "PT1H")

    schedule_url = (
        f"{HASL_SCHEDULE_BASE}{team.hasl_id}.htm"
        if getattr(team, "hasl_id", None)
        else None
    )

    for game in games:
        evt = Event()
        evt.add("uid", vText(f"{game.id}@hasl-calendar"))

        start = datetime.fromisoformat(game.datetime_local).replace(tzinfo=_eastern())
        end = start + timedelta(hours=1)

        address, field = _resolve_location(game.location)
        location_name = _location_name(game.location)

        # Requested team always first in the title
        is_home = game.home_team_slug == team.slug
        opponent = game.away_team.name if is_home else game.home_team.name
        summary = f"{team.name} vs {opponent}"

        # Description: web-site order first, then key/value fields
        desc_lines = [f"{game.home_team.name} vs {game.away_team.name}", ""]
        desc_lines.append(f"Location: {location_name}")
        if field:
            desc_lines.append(f"Field: {field}")
        desc_lines.append(f"League: {game.league}")
        if schedule_url:
            desc_lines.append(f"Schedule: {schedule_url}")

        evt.add("dtstart", start)
        evt.add("dtend", end)
        evt.add("summary", vText(summary))
        evt.add("location", vText(address))
        evt.add("description", vText("\n".join(desc_lines)))
        if schedule_url:
            evt.add("url", vText(schedule_url))
        evt.add("last-modified", datetime.now(tz=timezone.utc))

        cal.add_component(evt)

    return cal.to_ical()


def _eastern():
    import zoneinfo

    return zoneinfo.ZoneInfo("America/New_York")
