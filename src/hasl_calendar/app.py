from flask import Flask

from .models import init_db

app = Flask(__name__)


@app.before_request
def setup():
    init_db()


# Calendar feed routes will live here
# GET /calendar/<team_name>.ics  -> iCal feed for a team
# GET /teams                     -> list all known teams


if __name__ == "__main__":
    app.run(debug=True)
