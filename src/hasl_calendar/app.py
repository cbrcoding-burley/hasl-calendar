import functools
import logging
import os
from datetime import date

import jwt
from flask import Flask, Response, abort, jsonify, request

from .ical import build_feed
from .models import Game, Session, Team
from .scheduler import start as start_scheduler
from .scraper import sync_to_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = Flask(__name__)

start_scheduler(app)


def _require_sync_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        public_key = os.environ.get("SYNC_PUBLIC_KEY")
        auth = request.headers.get("Authorization", "")
        if not public_key or not auth.startswith("Bearer "):
            abort(401)
        try:
            jwt.decode(auth.removeprefix("Bearer "), public_key, algorithms=["RS256"])
        except jwt.PyJWTError:
            abort(401)
        return f(*args, **kwargs)

    return decorated


@app.get("/teams")
def list_teams():
    with Session() as session:
        teams = session.query(Team).order_by(Team.name).all()
        return jsonify([{"id": t.id, "name": t.name} for t in teams])


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


@app.get("/sync/state")
@_require_sync_auth
def sync_state():
    with Session() as session:
        game_ids = [row[0] for row in session.query(Game.id).all()]
        return jsonify({"game_ids": game_ids})


@app.post("/sync/upsert")
@_require_sync_auth
def sync_upsert():
    events = request.json.get("events", [])
    sync_to_db(events)
    return "", 204


@app.post("/sync/delete")
@_require_sync_auth
def sync_delete():
    game_ids = request.json.get("game_ids", [])
    today = date.today().isoformat()
    with Session() as session:
        session.query(Game).filter(
            Game.id.in_(game_ids),
            Game.date > today,
        ).delete(synchronize_session=False)
        session.commit()
    return "", 204


if __name__ == "__main__":
    app.run(debug=True)
