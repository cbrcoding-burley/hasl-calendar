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

Deployed to [Railway](https://railway.app) via GitHub Actions on pushes to `main`.
The database lives on a Railway volume mounted at `/data`.

See [`railway.toml`](railway.toml), [`.github/workflows/ci.yml`](.github/workflows/ci.yml),
and [`docs/railway.md`](docs/railway.md) for setup and configuration details.
