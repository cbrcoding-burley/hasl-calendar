import functools
import logging
import os
from datetime import date

import jwt
from flask import Flask, Response, abort, jsonify, render_template, request

from .ical import build_feed
from .models import Game, Session, SyncMeta, Team
from .scraper import sync_to_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)


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


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def healthz():
    return "", 204


@app.get("/teams")
def list_teams():
    with Session() as session:
        teams = session.query(Team).order_by(Team.name).all()
        return jsonify(
            [{"slug": t.slug, "name": t.name, "hasl_id": t.hasl_id} for t in teams]
        )


@app.get("/schedule/<slug>")
def team_schedule(slug: str):
    with Session() as session:
        team = session.query(Team).filter_by(slug=slug).first()
        if team is None:
            abort(404)
        games = (
            session.query(Game)
            .filter((Game.home_team_slug == slug) | (Game.away_team_slug == slug))
            .order_by(Game.date, Game.time)
            .all()
        )
        return jsonify(
            [
                {
                    "date": g.date,
                    "time": g.time,
                    "location": g.location,
                    "is_home": g.home_team_slug == slug,
                    "opponent": (
                        g.away_team.name
                        if g.home_team_slug == slug
                        else g.home_team.name
                    ),
                }
                for g in games
            ]
        )


@app.get("/calendar/<slug>.ics")
def team_calendar(slug: str):
    with Session() as session:
        team = session.query(Team).filter_by(slug=slug).first()
        if team is None:
            abort(404)

        games = (
            session.query(Game)
            .filter((Game.home_team_slug == slug) | (Game.away_team_slug == slug))
            .order_by(Game.date, Game.time)
            .all()
        )

        ical_bytes = build_feed(team, games)

    log.info(
        "calendar_request slug=%s games=%d bytes=%d", slug, len(games), len(ical_bytes)
    )
    return Response(
        ical_bytes,
        mimetype="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{slug}.ics"',
            "Cache-Control": "no-cache",
        },
    )


@app.get("/sync/state")
@_require_sync_auth
def sync_state():
    with Session() as session:
        game_ids = [row[0] for row in session.query(Game.id).all()]
        meta = session.get(SyncMeta, 1)
        return jsonify(
            {
                "game_ids": game_ids,
                "content_hash": meta.content_hash if meta else None,
                "last_full_sync_at": meta.last_full_sync_at if meta else None,
            }
        )


@app.post("/sync/upsert")
@_require_sync_auth
def sync_upsert():
    if not request.is_json:
        log.warning(
            "sync_upsert called with non-JSON body (content-type: %s)",
            request.content_type,
        )
        abort(400)
    body = request.json
    events = body.get("events", [])
    sync_to_db(events)
    content_hash = body.get("content_hash")
    synced_at = body.get("synced_at")
    if content_hash and synced_at:
        with Session() as session:
            meta = session.get(SyncMeta, 1)
            if meta is None:
                session.add(
                    SyncMeta(
                        id=1, content_hash=content_hash, last_full_sync_at=synced_at
                    )
                )
            else:
                meta.content_hash = content_hash
                meta.last_full_sync_at = synced_at
            session.commit()
    return "", 204


@app.post("/sync/delete")
@_require_sync_auth
def sync_delete():
    if not request.is_json:
        log.warning(
            "sync_delete called with non-JSON body (content-type: %s)",
            request.content_type,
        )
        abort(400)
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
