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
- **icalendar** — iCal feed generation
- **BeautifulSoup + lxml** — HTML scraping

## Local development

```bash
uv sync
uv run python seed.py          # one-off scrape + DB seed

# Dev server (auto-reloads, debug mode)
uv run flask --app hasl_calendar.app run --debug

# Production-like server (matches railway.toml)
uv run gunicorn 'hasl_calendar.app:app' --bind 0.0.0.0:8000 --workers 2
```

### Background syncing locally (not maintained)

In production the scraper runs as a separate Railway cron service. If you want
background syncing while developing locally, `dev/scheduler.py` is a
standalone APScheduler script that approximates this:

```bash
uv run python dev/scheduler.py &
```

This is not kept in sync with production — prefer `seed.py` for a one-off seed.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///hasl.db` | SQLAlchemy DB URL; set to `sqlite:////data/hasl.db` in production |

## Deployment

Deployed to [Railway](https://railway.app) via GitHub Actions on pushes to `main`.
The database lives on a Railway volume mounted at `/data`.

See [`railway.toml`](railway.toml), [`.github/workflows/ci.yml`](.github/workflows/ci.yml),
and [`docs/railway.md`](docs/railway.md) for setup and configuration details.
