import logging
import os

from flask import Flask, Response, abort, jsonify

from .ical import build_feed
from .models import Game, Session, Team, init_db, reset_db
from .scheduler import start as start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

if os.environ.get("RESET_DB_ON_START", "").lower() == "true":
    logger.warning("RESET_DB_ON_START is set — dropping and recreating all tables")
    reset_db()
else:
    init_db()

start_scheduler(app)


@app.get("/teams")
def list_teams():
    with Session() as session:
        teams = session.query(Team).order_by(Team.name).all()
        return jsonify(
            [{"id": t.id, "name": t.name, "league": t.league} for t in teams]
        )


@app.get("/calendar/<int:team_id>.ics")
def team_calendar(team_id: int):
    with Session() as session:
        team = session.get(Team, team_id)
        if team is None:
            abort(404)

        games = (
            session.query(Game)
            .filter((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
            .order_by(Game.date, Game.time)
            .all()
        )

        ical_bytes = build_feed(team, games)

    return Response(
        ical_bytes,
        mimetype="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{team_id}.ics"',
            "Cache-Control": "no-cache",
        },
    )


if __name__ == "__main__":
    app.run(debug=True)
