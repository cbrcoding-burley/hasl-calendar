import json

from hasl_calendar.models import Game, Session, Team, init_db
from hasl_calendar.scraper import fetch_and_parse, sync_to_db

if __name__ == "__main__":
    print("Fetching schedule...")
    events, league_index = fetch_and_parse()
    print("League index:", league_index)
    print(json.dumps(events[:3], indent=2))
    print(f"\nParsed {len(events)} events. Writing to DB...")

    sync_to_db(events)

    init_db()
    with Session() as session:
        team_count = session.query(Team).count()
        game_count = session.query(Game).count()
        print(f"DB: {team_count} teams, {game_count} games")

        print("\nSample teams:")
        for team in session.query(Team).limit(5).all():
            print(f"  {team}")

        print("\nSample games:")
        for game in session.query(Game).limit(3).all():
            print(
                f"  {game.date} {game.time} [{game.league}] {game.home_team.name} vs {game.away_team.name} @ {game.location}"
            )
