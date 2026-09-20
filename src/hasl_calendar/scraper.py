import hashlib
import json
import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

SCHEDULE_URL = "https://www.allprosoftware.net/HASLSUMMER23/aplsmasterschedule.htm"
TIMEZONE = "America/New_York"

_DATE_LOC_RE = re.compile(
    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(.+?)\s+(\d{4})\s+(.+)$"
)
_TEAM_ID_RE = re.compile(r"aplsteam(\d+)\.htm", re.IGNORECASE)
# Matches "S1 CO-ED REC LEAGUE" style lines in the schedule index block
_LEAGUE_INDEX_RE = re.compile(r"^(S\d)\s+(.+)$")


def _parse_header(text: str) -> tuple[str, str] | None:
    """Return (date_str, location) from a date+location header cell, or None."""
    m = _DATE_LOC_RE.match(text.strip())
    if not m:
        return None
    month_day, year, location = m.group(1), m.group(2), m.group(3)
    return f"{month_day.rstrip(',')} {year}", location.strip()


def _extract_team(cell) -> tuple[str, int | None]:
    """Return (name, team_id) from a team cell element."""
    a = cell.find("a")
    if a:
        name = a.get_text(strip=True)
        href = a.get("href", "")
        m = _TEAM_ID_RE.search(href)
        team_id = int(m.group(1)) if m else None
        return name, team_id
    return cell.get_text(strip=True), None


def parse_league_index(soup: BeautifulSoup) -> dict[str, str]:
    """Return {S-code: league name} by reading the index block at the top of the master schedule."""
    table = soup.find_all("table")[2]
    index_cell = table.find("tr").find_all(["td", "th"])[1]
    leagues = {}
    for line in index_cell.get_text(separator="\n").splitlines():
        m = _LEAGUE_INDEX_RE.match(line.strip())
        if m:
            leagues[m.group(1)] = m.group(2).strip()
    return leagues


def _game_id(date: str, time: str, home_id: int | None, away_id: int | None) -> str:
    key = f"{date}|{time}|{home_id}|{away_id}"
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
            _, time_str, league = texts[0], texts[1], texts[2]
            home_team_name, home_team_id = _extract_team(cells[3])
            away_team_name, away_team_id = _extract_team(cells[4])

            try:
                dt = datetime.strptime(
                    f"{current_date_str} {time_str.upper()}", "%B %d %Y %I:%M %p"
                )
            except ValueError:
                continue

            events.append(
                {
                    "id": _game_id(
                        dt.strftime("%Y-%m-%d"),
                        dt.strftime("%H:%M"),
                        home_team_id,
                        away_team_id,
                    ),
                    "date": dt.strftime("%Y-%m-%d"),
                    "time": dt.strftime("%H:%M"),
                    "datetime_local": dt.isoformat(),
                    "timezone": TIMEZONE,
                    "location": current_location,
                    "league": league,
                    "home_team_id": home_team_id,
                    "home_team_name": home_team_name,
                    "away_team_id": away_team_id,
                    "away_team_name": away_team_name,
                }
            )

    unique_team_ids = {e["home_team_id"] for e in events} | {
        e["away_team_id"] for e in events
    }
    log.info(
        "Parsed %d events, %d unique teams",
        len(events),
        len(unique_team_ids),
    )
    return events, league_index


def sync_to_db(events: list[dict]) -> None:
    from .models import Game, Session, Team, init_db

    init_db()
    teams_added = teams_updated = games_added = games_updated = 0

    with Session() as session:
        for event in events:
            for team_id, team_name in [
                (event["home_team_id"], event["home_team_name"]),
                (event["away_team_id"], event["away_team_name"]),
            ]:
                if team_id is None:
                    continue
                team = session.get(Team, team_id)
                if team is None:
                    session.add(Team(id=team_id, name=team_name))
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
                        home_team_id=event["home_team_id"],
                        away_team_id=event["away_team_id"],
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
    events, _ = fetch_and_parse()
    sync_to_db(events)


def sync_via_api(base_url: str, api_key: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    base_url = base_url.rstrip("/")

    state = requests.get(f"{base_url}/sync/state", headers=headers, timeout=15)
    state.raise_for_status()
    current_ids = set(state.json()["game_ids"])

    events, _ = fetch_and_parse()
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
