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
uv run flask --app hasl_calendar.app run --debug
```

See [docs/developers.md](docs/developers.md) for full setup, environment variables,
running the cron service locally, and test instructions.

## Deployment

Hosted on [Railway](https://railway.app) with Railway-native auto-deploys: pushes to `main` trigger Railway directly via its GitHub source connection. GitHub Actions runs tests only — no deploy step.

The database lives on a Railway persistent volume mounted at `/data`.

See [`railway.toml`](railway.toml) and [`docs/railway.md`](docs/railway.md) for infrastructure setup.
