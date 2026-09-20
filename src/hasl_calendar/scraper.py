import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone

import jwt
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


SCHEDULE_URL = "https://www.allprosoftware.net/HASLSUMMER23/aplsmasterschedule.htm"
TIMEZONE = "America/New_York"

TIME_AND_PLACE_REGEX = re.compile(
    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(.+?)\s+(\d{4})\s+(.+)$"
)
_TEAM_ID_REGEX = re.compile(r"aplsteam(\d+)\.htm", re.IGNORECASE)
# Matches "S1 CO-ED REC LEAGUE" style lines in the schedule index block
_LEAGUE_INDEX_REGEX = re.compile(r"^(S\d)\s+(.+)$")


def _parse_header(text: str) -> tuple[str, str] | None:
    """Return (date_str, location) from a date+location header cell, or None."""
    m = TIME_AND_PLACE_REGEX.match(text.strip())
    if not m:
        return None
    month_day, year, location = m.group(1), m.group(2), m.group(3)
    return f"{month_day.rstrip(',')} {year}", location.strip()


def _extract_team(cell) -> str:
    """Return team name from a team cell element."""
    a = cell.find("a")
    if a:
        return a.get_text(strip=True)
    return cell.get_text(strip=True)


def parse_league_index(soup: BeautifulSoup) -> dict[str, str]:
    """Return {S-code: league name} by reading the index block at the top of the master schedule."""
    table = soup.find_all("table")[2]
    index_cell = table.find("tr").find_all(["td", "th"])[1]
    leagues = {}
    for line in index_cell.get_text(separator="\n").splitlines():
        m = _LEAGUE_INDEX_REGEX.match(line.strip())
        if m:
            leagues[m.group(1)] = m.group(2).strip()
    return leagues


def _game_id(date: str, time: str, home_slug: str, away_slug: str) -> str:
    key = f"{date}|{time}|{home_slug}|{away_slug}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def fetch_and_parse(url: str = SCHEDULE_URL) -> tuple[list[dict], dict[str, str]]:
    """Return (events, league_index) where league_index maps S-code -> league name."""
    log.info("Fetching schedule from %s", url)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    events, league_index = parse_html(resp.text)
    log.info(
        "Fetch complete: %d events across %d leagues",
        len(events),
        len(league_index),
    )
    return events, league_index


def parse_html(html: str) -> tuple[list[dict], dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    league_index = parse_league_index(soup)
    schedule_table = soup.find_all("table")[2]

    events = []
    current_date_str: str | None = None
    current_location: str | None = None

    for row in schedule_table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        texts = [c.get_text(strip=True) for c in cells]

        if not texts:
            continue

        # Date+location header: single non-empty cell
        if len(cells) == 1 and texts[0]:
            parsed = _parse_header(texts[0])
            if parsed:
                current_date_str, current_location = parsed
            continue

        # Game row: blank | time | league | home_team | vs away_team
        if len(cells) == 5 and texts[0] == "" and current_date_str:
            _, time_str, league_code = texts[0], texts[1], texts[2]
            league = league_index.get(league_code)
            if league is None:
                log.warning(
                    "Unknown league code %r — defaulting to 'HASL'", league_code
                )
                league = "HASL"
            home_team_name = _extract_team(cells[3])
            away_team_name = _extract_team(cells[4])
            home_team_slug = _slugify(home_team_name)
            away_team_slug = _slugify(away_team_name)

            try:
                dt = datetime.strptime(
                    f"{current_date_str} {time_str.upper()}", "%B %d %Y %I:%M %p"
                )
            except ValueError:
                log.warning(
                    "Failed to parse datetime for row: date=%r time=%r — skipping",
                    current_date_str,
                    time_str,
                )
                continue

            events.append(
                {
                    "id": _game_id(
                        dt.strftime("%Y-%m-%d"),
                        dt.strftime("%H:%M"),
                        home_team_slug,
                        away_team_slug,
                    ),
                    "date": dt.strftime("%Y-%m-%d"),
                    "time": dt.strftime("%H:%M"),
                    "datetime_local": dt.isoformat(),
                    "timezone": TIMEZONE,
                    "location": current_location,
                    "league": league,
                    "home_team_slug": home_team_slug,
                    "home_team_name": home_team_name,
                    "away_team_slug": away_team_slug,
                    "away_team_name": away_team_name,
                }
            )

    unique_team_slugs = {e["home_team_slug"] for e in events} | {
        e["away_team_slug"] for e in events
    }
    if not events:
        raise ValueError("Parsed 0 events — page structure may have changed")
    log.info(
        "Parsed %d events, %d unique teams",
        len(events),
        len(unique_team_slugs),
    )
    return events, league_index


def sync_to_db(events: list[dict]) -> None:
    from .models import Game, Session, Team, init_db

    init_db()
    teams_added = teams_updated = games_added = games_updated = 0

    with Session() as session:
        for event in events:
            for team_slug, team_name in [
                (event["home_team_slug"], event["home_team_name"]),
                (event["away_team_slug"], event["away_team_name"]),
            ]:
                team = session.get(Team, team_slug)
                if team is None:
                    session.add(Team(slug=team_slug, name=team_name))
                    teams_added += 1
                elif team.name != team_name:
                    team.name = team_name
                    teams_updated += 1

            game = session.get(Game, event["id"])
            if game is None:
                session.add(
                    Game(
                        id=event["id"],
                        date=event["date"],
                        time=event["time"],
                        datetime_local=event["datetime_local"],
                        timezone=event["timezone"],
                        location=event["location"],
                        league=event["league"],
                        home_team_slug=event["home_team_slug"],
                        away_team_slug=event["away_team_slug"],
                    )
                )
                games_added += 1
            else:
                # Update mutable fields in case the schedule changed
                game.date = event["date"]
                game.time = event["time"]
                game.datetime_local = event["datetime_local"]
                game.location = event["location"]
                game.league = event["league"]
                games_updated += 1

        session.commit()

    log.info(
        "DB sync complete: %d teams added, %d updated; %d games added, %d updated",
        teams_added,
        teams_updated,
        games_added,
        games_updated,
    )


def sync_schedule() -> None:
    events, league_index = fetch_and_parse()
    log.info("Leagues: %s", list(league_index.values()))
    sync_to_db(events)


def _make_sync_token() -> str:
    private_key = os.environ["SYNC_PRIVATE_KEY"]
    now = datetime.now(tz=timezone.utc)
    return jwt.encode(
        {"sub": "scraper", "iat": now, "exp": now + timedelta(minutes=5)},
        private_key,
        algorithm="RS256",
    )


def sync_via_api(base_url: str) -> None:
    headers = {
        "Authorization": f"Bearer {_make_sync_token()}",
        "Content-Type": "application/json",
    }
    base_url = base_url.rstrip("/")

    state = requests.get(f"{base_url}/sync/state", headers=headers, timeout=15)
    state.raise_for_status()
    current_ids = set(state.json()["game_ids"])

    events, league_index = fetch_and_parse()
    log.info("Leagues in scraped data: %s", list(league_index.values()))
    parsed_ids = {e["id"] for e in events}

    resp = requests.post(
        f"{base_url}/sync/upsert", json={"events": events}, headers=headers, timeout=30
    )
    resp.raise_for_status()
    log.info("Upserted %d events", len(events))

    orphan_ids = list(current_ids - parsed_ids)
    if orphan_ids:
        resp = requests.post(
            f"{base_url}/sync/delete",
            json={"game_ids": orphan_ids},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        log.info(
            "Submitted %d orphan IDs for deletion (future-only filtered server-side)",
            len(orphan_ids),
        )


if __name__ == "__main__":
    events, league_index = fetch_and_parse()
    print("League index:", league_index)
    print(json.dumps(events[:5], indent=2))
    print(f"\nTotal events: {len(events)}")
