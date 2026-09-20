# hasl-calendar

Scrapes the [HASL](https://www.allprosoftware.net/HASLSUMMER23/aplsmasterschedule.htm) master schedule and serves per-team iCal feeds over HTTP.

## What it does

- Periodically fetches the HASL schedule page and parses game data
- Stores games in a SQLite database
- Exposes `/calendar/<team>.ics` endpoints that any calendar app can subscribe to
- Runs on Railway with a persistent volume for the database

## Stack

- **Python 3.11+** with [uv](https://github.com/astral-sh/uv) for dependency management
- **Flask** — HTTP server
- **SQLAlchemy** — database ORM (SQLite)
- **APScheduler** — background scrape job (every ~6 hours)
- **icalendar** — iCal feed generation
- **BeautifulSoup + lxml** — HTML scraping

## Local development

```bash
uv sync
uv run python main.py          # one-off scrape to stdout
uv run flask --app hasl_calendar.app run --debug
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///hasl.db` | SQLAlchemy DB URL; set to `sqlite:////data/hasl.db` in production |

## Deployment

Deployed to [Railway](https://railway.app) via GitLab CI on pushes to `main`.
The database lives on a Railway volume mounted at `/data`.

See `.gitlab-ci.yml` and `railway.toml` for details.
