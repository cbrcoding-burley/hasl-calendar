from hasl_calendar.scraper import _game_id, parse_html
from tests.conftest import SCHEDULE_HTML


class TestParseLeagueIndex:
    def test_returns_all_four_leagues(self, parsed_schedule):
        _, league_index = parsed_schedule
        assert league_index == {
            "S1": "CO-ED REC LEAGUE",
            "S2": "CO-ED WORLD LEAGUE",
            "S3": "MEN'S REC LEAGUE",
            "S4": "MEN'S USA LEAGUE",
        }

    def test_keys_are_s_codes(self, parsed_schedule):
        _, league_index = parsed_schedule
        assert all(k.startswith("S") and k[1:].isdigit() for k in league_index)


class TestParseHtml:
    def test_event_count(self, parsed_schedule):
        events, _ = parsed_schedule
        assert len(events) == 3

    def test_first_event_date_and_time(self, parsed_schedule):
        events, _ = parsed_schedule
        assert events[0]["date"] == "2026-09-08"
        assert events[0]["time"] == "21:00"

    def test_first_event_location(self, parsed_schedule):
        events, _ = parsed_schedule
        assert events[0]["location"] == "FRANK SINATRA PARK - NORTH"

    def test_first_event_league(self, parsed_schedule):
        events, _ = parsed_schedule
        assert events[0]["league"] == "MEN'S REC LEAGUE"

    def test_first_event_teams(self, parsed_schedule):
        events, _ = parsed_schedule
        assert events[0]["home_team_name"] == "Soccer Monday's"
        assert events[0]["away_team_name"] == "TEK FC"

    def test_team_ids_parsed_from_hrefs(self, parsed_schedule):
        events, _ = parsed_schedule
        assert events[0]["home_team_id"] == 654
        assert events[0]["away_team_id"] == 655

    def test_second_date_section_parsed(self, parsed_schedule):
        events, _ = parsed_schedule
        # Third event is from the second date header (Sep 9)
        assert events[2]["date"] == "2026-09-09"
        assert events[2]["location"] == "1600 PARK SOUTH"

    def test_datetime_local_is_iso(self, parsed_schedule):
        events, _ = parsed_schedule
        assert events[0]["datetime_local"] == "2026-09-08T21:00:00"

    def test_timezone_field(self, parsed_schedule):
        events, _ = parsed_schedule
        assert events[0]["timezone"] == "America/New_York"

    def test_event_has_stable_id(self, parsed_schedule):
        events, _ = parsed_schedule
        assert len(events[0]["id"]) == 16
        assert events[0]["id"].isalnum()

    def test_pm_time_parsed_to_24h(self, parsed_schedule):
        events, _ = parsed_schedule
        # "10:00 pm" → "22:00"
        assert events[1]["time"] == "22:00"

    def test_different_games_have_different_ids(self, parsed_schedule):
        events, _ = parsed_schedule
        ids = [e["id"] for e in events]
        assert len(ids) == len(set(ids))


class TestGameId:
    def test_same_inputs_produce_same_id(self):
        a = _game_id("2026-09-08", "21:00", 654, 655)
        b = _game_id("2026-09-08", "21:00", 654, 655)
        assert a == b

    def test_different_date_produces_different_id(self):
        assert _game_id("2026-09-08", "21:00", 654, 655) != _game_id(
            "2026-09-09", "21:00", 654, 655
        )

    def test_different_time_produces_different_id(self):
        assert _game_id("2026-09-08", "21:00", 654, 655) != _game_id(
            "2026-09-08", "22:00", 654, 655
        )

    def test_different_teams_produce_different_id(self):
        assert _game_id("2026-09-08", "21:00", 654, 655) != _game_id(
            "2026-09-08", "21:00", 656, 658
        )

    def test_location_change_does_not_change_id(self):
        # Rescheduling a venue updates the event in place rather than deleting+recreating it
        html_north = SCHEDULE_HTML
        html_south = SCHEDULE_HTML.replace(
            "FRANK SINATRA PARK - NORTH", "FRANK SINATRA PARK - SOUTH"
        )
        events_north, _ = parse_html(html_north)
        events_south, _ = parse_html(html_south)
        assert events_north[0]["id"] == events_south[0]["id"]

    def test_id_is_16_hex_chars(self):
        game_id = _game_id("2026-09-08", "21:00", 654, 655)
        assert len(game_id) == 16
        assert all(c in "0123456789abcdef" for c in game_id)
