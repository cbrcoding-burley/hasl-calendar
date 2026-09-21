"""Integration tests: parse_html → sync_to_db → Flask routes → iCal output.

No network calls. date.today() is frozen to 2026-10-01:
  Sep 8–9 games are PAST, Nov 1 games are FUTURE.

Teams and game counts:
  Soccer Monday's : Sep 8 9pm  vs TEK FC         | Nov 1 8pm vs Absent Fathers
  TEK FC          : Sep 8 9pm  (away)             | Nov 1 9pm vs Clare Bears (away)
  Absent Fathers  : Sep 8 10pm vs Ted's Lasso     | Nov 1 8pm (away)
  Clare Bears     : Sep 9 9pm  vs Boozin' Benders | Nov 1 9pm vs TEK FC
  Ted's Lasso     : Sep 8 10pm (away only)
  Boozin' Benders : Sep 9 9pm  (away only)
"""

import importlib
from datetime import date, datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from icalendar import Calendar

# ── auth ──────────────────────────────────────────────────────────────────────


def _generate_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    pub = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return priv, pub


PRIVATE_KEY, PUBLIC_KEY = _generate_keypair()


def _token():
    now = datetime.now(tz=timezone.utc)
    return jwt.encode(
        {"sub": "scraper", "iat": now, "exp": now + timedelta(minutes=5)},
        PRIVATE_KEY,
        algorithm="RS256",
    )


# ── HTML building blocks ───────────────────────────────────────────────────────

_HTML_HEADER = """\
<html><body>
<table><tr><td>HOBOKEN ADULT SOCCER LEAGUE</td></tr></table>
<table><tr><td>Master Schedule</td></tr></table>
<table>
  <tr>
    <td>Nav</td>
    <td valign="top">
      <b>
        S1 CO-ED REC LEAGUE<br/>
        S2 CO-ED WORLD LEAGUE<br/>
        S3 MEN'S REC LEAGUE<br/>
        S4 MEN'S USA LEAGUE<br/>
      </b>
      <table border="0" cellspacing="10">"""

_HTML_FOOTER = """
      </table>
    </td>
  </tr>
</table>
</body></html>"""

_SEP8_BLOCK = """
        <tr><td colspan="5"><b>Tuesday, September 8, 2026 FRANK SINATRA PARK - NORTH</b></td></tr>
        <tr>
          <td><img src="s.gif" width="20"/></td>
          <td>9:00 pm</td><td>S3</td>
          <td><a href="#">Soccer Monday's</a></td>
          <td> vs <a href="#">TEK FC</a></td>
        </tr>
        <tr>
          <td><img src="s.gif" width="20"/></td>
          <td>10:00 pm</td><td>S4</td>
          <td><a href="#">Absent Fathers</a></td>
          <td> vs <a href="#">Ted's Lasso</a></td>
        </tr>"""

_SEP9_BLOCK = """
        <tr><td colspan="5"><b>Wednesday, September 9, 2026 1600 PARK SOUTH</b></td></tr>
        <tr>
          <td><img src="s.gif" width="20"/></td>
          <td>9:00 pm</td><td>S1</td>
          <td><a href="#">Clare Bears</a></td>
          <td> vs <a href="#">Boozin' Benders FC</a></td>
        </tr>"""

_NOV1_BLOCK = """
        <tr><td colspan="5"><b>Sunday, November 1, 2026 FRANK SINATRA PARK - SOUTH</b></td></tr>
        <tr>
          <td><img src="s.gif" width="20"/></td>
          <td>8:00 pm</td><td>S3</td>
          <td><a href="#">Soccer Monday's</a></td>
          <td> vs <a href="#">Absent Fathers</a></td>
        </tr>
        <tr>
          <td><img src="s.gif" width="20"/></td>
          <td>9:00 pm</td><td>S1</td>
          <td><a href="#">Clare Bears</a></td>
          <td> vs <a href="#">TEK FC</a></td>
        </tr>"""

# Nov 1 block without Soccer Monday's game (Clare Bears vs TEK FC still on)
_NOV1_BLOCK_NO_SM = """
        <tr><td colspan="5"><b>Sunday, November 1, 2026 FRANK SINATRA PARK - SOUTH</b></td></tr>
        <tr>
          <td><img src="s.gif" width="20"/></td>
          <td>9:00 pm</td><td>S1</td>
          <td><a href="#">Clare Bears</a></td>
          <td> vs <a href="#">TEK FC</a></td>
        </tr>"""

# Full schedule: 5 games across 3 dates
RICH_HTML = _HTML_HEADER + _SEP8_BLOCK + _SEP9_BLOCK + _NOV1_BLOCK + _HTML_FOOTER

# Only past games remain (no Nov 1 block) — simulates site dropping future games
RICH_HTML_NO_NOV1 = _HTML_HEADER + _SEP8_BLOCK + _SEP9_BLOCK + _HTML_FOOTER

# Soccer Monday's Nov 1 game cancelled; Clare Bears vs TEK FC still on
RICH_HTML_NO_SM_NOV1 = (
    _HTML_HEADER + _SEP8_BLOCK + _SEP9_BLOCK + _NOV1_BLOCK_NO_SM + _HTML_FOOTER
)

# Nov 1 games relocated to Resiliency Park (resolves to "1201 Madison St")
RICH_HTML_NOV1_RESILIENCY = RICH_HTML.replace(
    "FRANK SINATRA PARK - SOUTH", "RESILIENCY PARK"
)

# Soccer Monday's Nov 1 game moved to 7:00 pm (time shift → new game ID)
RICH_HTML_NOV1_SM_EARLY = RICH_HTML.replace("<td>8:00 pm</td>", "<td>7:00 pm</td>")

# Sep 8 games dropped off site (they're over) but Nov 1 still upcoming
RICH_HTML_NO_SEP8 = _HTML_HEADER + _SEP9_BLOCK + _NOV1_BLOCK + _HTML_FOOTER


# ── helpers ───────────────────────────────────────────────────────────────────


def _ical_events(client, slug):
    resp = client.get(f"/calendar/{slug}.ics")
    cal = Calendar.from_ical(resp.data)
    return sorted(
        [c for c in cal.walk() if c.name == "VEVENT"],
        key=lambda e: e["dtstart"].dt,
    )


def _sync(client, auth_headers, html):
    """Replicate sync_via_api using the test client instead of real HTTP.

    All DB writes go through the server's HTTP endpoints — never direct DB access.
    """
    from hasl_calendar.scraper import parse_html

    current_ids = set(client.get("/sync/state", headers=auth_headers).json["game_ids"])
    events, _ = parse_html(html)
    client.post("/sync/upsert", json={"events": events}, headers=auth_headers)
    orphan_ids = list(current_ids - {e["id"] for e in events})
    if orphan_ids:
        client.post("/sync/delete", json={"game_ids": orphan_ids}, headers=auth_headers)


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def auth():
    return {"Authorization": f"Bearer {_token()}"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("SYNC_PUBLIC_KEY", PUBLIC_KEY)

    import hasl_calendar.app as app_mod
    import hasl_calendar.models as models_mod

    importlib.reload(models_mod)
    models_mod.init_db()
    importlib.reload(app_mod)

    # Freeze date.today() to 2026-10-01 so Sep games are past, Nov games are future.
    _frozen = date(2026, 10, 1)

    class _FrozenDate:
        @staticmethod
        def today():
            return _frozen

    monkeypatch.setattr(app_mod, "date", _FrozenDate)
    app_mod.app.config["TESTING"] = True
    with app_mod.app.test_client() as c:
        yield c


@pytest.fixture
def seeded_client(client, auth):
    _sync(client, auth, RICH_HTML)
    return client


# ── 1. Build from scratch ─────────────────────────────────────────────────────


class TestBuildFromScratch:
    def test_all_teams_created(self, seeded_client):
        slugs = {t["slug"] for t in seeded_client.get("/teams").json}
        assert slugs == {
            "soccer-monday-s",
            "tek-fc",
            "absent-fathers",
            "ted-s-lasso",
            "clare-bears",
            "boozin-benders-fc",
        }

    def test_team_names_correct(self, seeded_client):
        by_slug = {t["slug"]: t["name"] for t in seeded_client.get("/teams").json}
        assert by_slug["soccer-monday-s"] == "Soccer Monday's"
        assert by_slug["boozin-benders-fc"] == "Boozin' Benders FC"

    def test_multi_game_teams_have_two_events(self, seeded_client):
        for slug in ("soccer-monday-s", "tek-fc", "absent-fathers", "clare-bears"):
            events = _ical_events(seeded_client, slug)
            assert len(events) == 2, f"{slug}: expected 2, got {len(events)}"

    def test_single_game_teams_have_one_event(self, seeded_client):
        for slug in ("ted-s-lasso", "boozin-benders-fc"):
            events = _ical_events(seeded_client, slug)
            assert len(events) == 1, f"{slug}: expected 1, got {len(events)}"

    def test_correct_opponents_across_both_games(self, seeded_client):
        events = _ical_events(seeded_client, "soccer-monday-s")
        summaries = [str(e["summary"]) for e in events]
        assert summaries[0] == "Soccer Monday's vs TEK FC"  # Sep 8
        assert summaries[1] == "Soccer Monday's vs Absent Fathers"  # Nov 1

    def test_idempotent_sync_does_not_duplicate(self, seeded_client, auth):
        _sync(seeded_client, auth, RICH_HTML)  # second sync
        events = _ical_events(seeded_client, "soccer-monday-s")
        assert len(events) == 2


# ── 2. Update time and location ───────────────────────────────────────────────


class TestUpdateTimeAndLocation:
    def test_location_change_updates_only_nov1_game(self, seeded_client, auth):
        _sync(seeded_client, auth, RICH_HTML_NOV1_RESILIENCY)
        events = _ical_events(seeded_client, "soccer-monday-s")

        # Sep 8 game: still at Sinatra Park
        assert str(events[0]["location"]) == "398 Sinatra Dr, Hoboken, NJ 07030"
        # Nov 1 game: moved to Resiliency Park
        assert str(events[1]["location"]) == "1201 Madison St, Hoboken, NJ 07030"

    def test_location_change_affects_both_nov1_games(self, seeded_client, auth):
        _sync(seeded_client, auth, RICH_HTML_NOV1_RESILIENCY)
        # Clare Bears Nov 1 game also at the same date block → also updated
        cb_events = _ical_events(seeded_client, "clare-bears")
        nov1_event = next(e for e in cb_events if e["dtstart"].dt.month == 11)
        assert str(nov1_event["location"]) == "1201 Madison St, Hoboken, NJ 07030"

    def test_unrelated_sep9_location_unchanged(self, seeded_client, auth):
        before = str(_ical_events(seeded_client, "clare-bears")[0]["location"])
        _sync(seeded_client, auth, RICH_HTML_NOV1_RESILIENCY)
        after = str(_ical_events(seeded_client, "clare-bears")[0]["location"])
        assert before == after  # Sep 9 game untouched

    def test_time_change_replaces_future_game(self, seeded_client, auth):
        _sync(seeded_client, auth, RICH_HTML_NOV1_SM_EARLY)
        events = _ical_events(seeded_client, "soccer-monday-s")
        assert len(events) == 2
        # Sep 8 game still at 21:00
        assert events[0]["dtstart"].dt.hour == 21
        # Nov 1 game now at 19:00 (old 20:00 entry was a future orphan → deleted)
        assert events[1]["dtstart"].dt.hour == 19

    def test_time_change_does_not_affect_sep8_game(self, seeded_client, auth):
        sep8_before = _ical_events(seeded_client, "soccer-monday-s")[0]["dtstart"].dt
        _sync(seeded_client, auth, RICH_HTML_NOV1_SM_EARLY)
        sep8_after = _ical_events(seeded_client, "soccer-monday-s")[0]["dtstart"].dt
        assert sep8_before == sep8_after


# ── 3. Remove a future event ──────────────────────────────────────────────────


class TestRemoveFutureEvent:
    def test_cancelled_future_game_removed_from_calendar(self, seeded_client, auth):
        _sync(seeded_client, auth, RICH_HTML_NO_SM_NOV1)
        events = _ical_events(seeded_client, "soccer-monday-s")
        assert len(events) == 1
        assert events[0]["dtstart"].dt.month == 9  # only Sep 8 game remains

    def test_opponent_also_loses_the_game(self, seeded_client, auth):
        # Absent Fathers' only game was Nov 1 as away — it should also disappear
        _sync(seeded_client, auth, RICH_HTML_NO_SM_NOV1)
        events = _ical_events(seeded_client, "absent-fathers")
        assert len(events) == 1
        assert events[0]["dtstart"].dt.month == 9  # Sep 8 game vs Ted's Lasso remains

    def test_other_nov1_game_unaffected(self, seeded_client, auth):
        # Clare Bears vs TEK FC on Nov 1 is a different game — stays on schedule
        _sync(seeded_client, auth, RICH_HTML_NO_SM_NOV1)
        cb_events = _ical_events(seeded_client, "clare-bears")
        assert len(cb_events) == 2
        assert any(e["dtstart"].dt.month == 11 for e in cb_events)


# ── 4. Time passing: past games drop off the site ─────────────────────────────


class TestTimePassingPastGamesDropOff:
    def test_past_sep8_games_not_deleted_when_dropped_from_site(
        self, seeded_client, auth
    ):
        # Site stops listing Sep 8 games after they're played
        _sync(seeded_client, auth, RICH_HTML_NO_SEP8)
        events = _ical_events(seeded_client, "soccer-monday-s")
        # date guard in /sync/delete blocks deletion of past games
        assert any(
            e["dtstart"].dt.month == 9 for e in events
        ), "Sep 8 game is past — server-side date guard should protect it"

    def test_future_nov1_game_survives_sep8_drop(self, seeded_client, auth):
        _sync(seeded_client, auth, RICH_HTML_NO_SEP8)
        events = _ical_events(seeded_client, "soccer-monday-s")
        assert any(e["dtstart"].dt.month == 11 for e in events)

    def test_future_nov1_game_deleted_when_dropped_from_site(self, seeded_client, auth):
        _sync(seeded_client, auth, RICH_HTML_NO_NOV1)
        events = _ical_events(seeded_client, "soccer-monday-s")
        assert all(
            e["dtstart"].dt.month != 11 for e in events
        ), "Nov 1 game is future — orphan deletion should remove it"

    def test_past_games_preserved_when_future_dropped(self, seeded_client, auth):
        _sync(seeded_client, auth, RICH_HTML_NO_NOV1)
        events = _ical_events(seeded_client, "soccer-monday-s")
        assert len(events) == 1
        assert events[0]["dtstart"].dt.month == 9
