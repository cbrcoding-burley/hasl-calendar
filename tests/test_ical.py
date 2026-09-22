import pytest
from icalendar import Calendar

from tests.conftest import make_game, make_team  # noqa: F401 (used in inline tests)


@pytest.fixture
def home_team():
    return make_team("Soccer Monday's")


@pytest.fixture
def away_team():
    return make_team("TEK FC")


@pytest.fixture
def single_game(home_team, away_team):
    return make_game(
        id="af6865404c8f5c0b",
        home_team=home_team,
        away_team=away_team,
        date="2026-09-08",
        time="21:00",
        location="FRANK SINATRA PARK - NORTH",
    )


@pytest.fixture
def feed_bytes(home_team, single_game):
    from hasl_calendar.ical import build_feed

    return build_feed(home_team, [single_game])


@pytest.fixture
def parsed_feed(feed_bytes):
    return Calendar.from_ical(feed_bytes)


class TestBuildFeedStructure:
    def test_output_is_bytes(self, feed_bytes):
        assert isinstance(feed_bytes, bytes)

    def test_parses_as_valid_icalendar(self, parsed_feed):
        assert parsed_feed is not None

    def test_calendar_version(self, parsed_feed):
        assert str(parsed_feed["version"]) == "2.0"

    def test_calendar_name_includes_team_name(self, parsed_feed, home_team):
        calname = str(parsed_feed["x-wr-calname"])
        assert home_team.name in calname

    def test_empty_game_list_produces_valid_feed(self, home_team):
        from hasl_calendar.ical import build_feed

        cal_bytes = build_feed(home_team, [])
        cal = Calendar.from_ical(cal_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert events == []


class TestBuildFeedEvents:
    def test_one_event_per_game(self, parsed_feed):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        assert len(events) == 1

    def test_uid_format(self, parsed_feed, single_game):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        assert str(events[0]["uid"]) == f"{single_game.id}@hasl-calendar"

    def test_summary_puts_requested_team_first_when_home(
        self, parsed_feed, home_team, away_team
    ):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        assert str(events[0]["summary"]) == f"{home_team.name} vs {away_team.name}"

    def test_summary_puts_requested_team_first_when_away(self, home_team, away_team):
        from hasl_calendar.ical import build_feed

        game = make_game("g1", home_team, away_team)
        cal = Calendar.from_ical(build_feed(away_team, [game]))
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert str(events[0]["summary"]) == f"{away_team.name} vs {home_team.name}"

    def test_description_first_line_is_home_vs_away(
        self, parsed_feed, home_team, away_team
    ):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        first_line = str(events[0]["description"]).splitlines()[0]
        assert first_line == f"{home_team.name} vs {away_team.name}"

    def test_location_is_street_address(self, parsed_feed):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        assert str(events[0]["location"]) == "398 Sinatra Dr, Hoboken, NJ 07030"

    def test_description_includes_location_name(self, parsed_feed):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        assert "Location: Frank Sinatra Park" in str(events[0]["description"])

    def test_description_includes_field(self, parsed_feed):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        assert "Field: North" in str(events[0]["description"])

    def test_description_includes_league(self, parsed_feed):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        assert "League: MEN'S REC LEAGUE" in str(events[0]["description"])

    def test_url_set_when_hasl_id_present(self, home_team, away_team):
        from hasl_calendar.ical import build_feed

        team_with_id = make_team("Soccer Monday's", hasl_id="654")
        game = make_game("g1", team_with_id, away_team)
        cal = Calendar.from_ical(build_feed(team_with_id, [game]))
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert "aplsteam654.htm" in str(events[0]["url"])

    def test_url_not_set_when_no_hasl_id(self, away_team):
        from hasl_calendar.ical import build_feed

        team_no_id = make_team("No ID Team")
        game = make_game("g1", team_no_id, away_team)
        cal = Calendar.from_ical(build_feed(team_no_id, [game]))
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert events[0].get("url") is None

    def test_dtstart_correct_date_and_time(self, parsed_feed):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        dtstart = events[0]["dtstart"].dt
        assert dtstart.year == 2026
        assert dtstart.month == 9
        assert dtstart.day == 8
        assert dtstart.hour == 21
        assert dtstart.minute == 0

    def test_dtend_is_one_hour_after_dtstart(self, parsed_feed):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        evt = events[0]
        delta = evt["dtend"].dt - evt["dtstart"].dt
        assert delta.total_seconds() == 3600

    def test_dtstart_is_timezone_aware(self, parsed_feed):
        events = [c for c in parsed_feed.walk() if c.name == "VEVENT"]
        assert events[0]["dtstart"].dt.tzinfo is not None

    def test_multiple_games_all_present(self, home_team, away_team):
        from hasl_calendar.ical import build_feed

        dates = ["2026-09-08", "2026-09-15", "2026-09-22"]
        games = [
            make_game(f"id{i}", home_team, away_team, date=dates[i], time="21:00")
            for i in range(3)
        ]
        cal = Calendar.from_ical(build_feed(home_team, games))
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert len(events) == 3

    def test_event_uids_are_unique(self, home_team, away_team):
        from hasl_calendar.ical import build_feed

        dates = ["2026-09-08", "2026-09-15", "2026-09-22"]
        games = [
            make_game(f"id{i}", home_team, away_team, date=dates[i], time="21:00")
            for i in range(3)
        ]
        cal = Calendar.from_ical(build_feed(home_team, games))
        uids = [str(c["uid"]) for c in cal.walk() if c.name == "VEVENT"]
        assert len(uids) == len(set(uids))
