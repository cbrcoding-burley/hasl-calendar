"""Shared fixtures. All HTML is static — no network calls anywhere in the test suite."""

from types import SimpleNamespace

import pytest

# Minimal but structurally faithful replica of the real schedule page.
# Three outer tables match the real page's table[0]/[1]/[2] layout.
# The nested game table inside table[2] uses the exact same tag/attribute
# structure the real page uses, so the same parser logic applies.
SCHEDULE_HTML = """
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
      <table border="0" cellspacing="10">
        <tr>
          <td colspan="5"><b>Tuesday, September 8, 2026 FRANK SINATRA PARK - NORTH</b></td>
        </tr>
        <tr>
          <td><img src="spacer.gif" width="20"/></td>
          <td>9:00 pm</td>
          <td>S3</td>
          <td><a href="aplsteam654.htm">Soccer Monday's</a></td>
          <td> vs <a href="aplsteam655.htm">TEK FC</a></td>
        </tr>
        <tr>
          <td><img src="spacer.gif" width="20"/></td>
          <td>10:00 pm</td>
          <td>S4</td>
          <td><a href="aplsteam656.htm">Absent Fathers</a></td>
          <td> vs <a href="aplsteam658.htm">Ted's Lasso</a></td>
        </tr>
        <tr>
          <td colspan="5"><b>Wednesday, September 9, 2026 1600 PARK SOUTH</b></td>
        </tr>
        <tr>
          <td><img src="spacer.gif" width="20"/></td>
          <td>9:00 pm</td>
          <td>S1</td>
          <td><a href="aplsteam410.htm">Clare Bears</a></td>
          <td> vs <a href="aplsteam413.htm">Boozin' Benders FC</a></td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body></html>
"""


@pytest.fixture
def schedule_html():
    return SCHEDULE_HTML


@pytest.fixture
def parsed_schedule(schedule_html):
    from hasl_calendar.scraper import parse_html

    events, league_index = parse_html(schedule_html)
    return events, league_index


def make_team(name: str, slug: str = None):
    from hasl_calendar.scraper import _slugify

    return SimpleNamespace(name=name, slug=slug or _slugify(name))


def make_game(
    id: str,
    home_team,
    away_team,
    date: str = "2026-09-08",
    time: str = "21:00",
    location: str = "FRANK SINATRA PARK - NORTH",
    league: str = "MEN'S REC LEAGUE",
):
    return SimpleNamespace(
        id=id,
        date=date,
        time=time,
        datetime_local=f"{date}T{time}:00",
        timezone="America/New_York",
        location=location,
        league=league,
        home_team=home_team,
        away_team=away_team,
        home_team_slug=home_team.slug,
        away_team_slug=away_team.slug,
    )
