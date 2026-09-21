# Developer Guide

## Architecture

Two services share the same GitHub repo and deploy together:

| Service | Type | Role |
|---|---|---|
| `hasl-calendar` | Web (always-on) | Serves iCal feeds; exposes the authenticated sync API |
| `hasl-calendar-cron` | Cron (`0 */6 * * *`) | Scrapes HASL schedule page; pushes updates to the web service |

The cron service never touches the database directly. It calls the web service's
sync API, which owns all writes. On Railway, cron reaches web over the private
network (`hasl-calendar.railway.internal:8080`) — no public internet involved.

The SQLite database lives on a persistent volume mounted at `/data` on the web
service only.

### Sync auth

`/sync/state`, `/sync/upsert`, and `/sync/delete` require a Bearer JWT signed
with an RSA-256 private key. The cron service holds the private key; the web
service holds the matching public key. Tokens expire after 5 minutes. This
prevents unauthenticated writes to the calendar data.

---

## Environment variables

### `hasl-calendar` (web)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite:///hasl.db` | SQLAlchemy DB URL. Production uses `sqlite:////data/hasl.db` |
| `SYNC_PUBLIC_KEY` | Yes (sync endpoints) | — | RSA public key PEM. Sync routes return 401 without it |

### `hasl-calendar-cron`

| Variable | Required | Default | Description |
|---|---|---|---|
| `HASL_CALENDAR_URL` | Yes | — | Base URL of the web service, e.g. `http://hasl-calendar.railway.internal:8080` |
| `SYNC_PRIVATE_KEY` | Yes | — | RSA private key PEM used to sign sync JWTs |

---

## Generating the sync keypair

Keys live in `.secrets/` (gitignored). To regenerate:

```bash
mkdir -p .secrets
openssl genrsa -out .secrets/private_key.pem 2048
openssl rsa -in .secrets/private_key.pem -pubout -out .secrets/public_key.pem
```

Use separate keypairs per environment (staging and production) so a staging
compromise can't forge production sync calls.

---

## Running locally

### Web service

```bash
uv sync

# Dev server (auto-reloads)
uv run flask --app hasl_calendar.app run --debug

# Production-like (matches railway.toml)
uv run gunicorn 'hasl_calendar.app:app' --bind 0.0.0.0:8000 --workers 2
```

The web service starts fine without `SYNC_PUBLIC_KEY` — sync endpoints just
return 401. Set it if you're testing the sync flow:

```bash
export SYNC_PUBLIC_KEY="$(cat .secrets/public_key.pem)"
```

### One-off schedule sync

Scrapes the HASL page and pushes updates to a running web service:

```bash
export HASL_CALENDAR_URL="http://localhost:5000"
export SYNC_PRIVATE_KEY="$(cat .secrets/private_key.pem)"
uv run python -m hasl_calendar.sync_cron
```

Alternatively, `seed.py` writes directly to the local DB without going through
the sync API — useful for a quick first-time seed:

```bash
uv run python seed.py
```

### Background syncing (dev only, not maintained)

`dev/scheduler.py` is a standalone APScheduler script that approximates the
Railway cron service locally. It's not kept in sync with production — prefer
the one-off sync above.

```bash
uv run python dev/scheduler.py &
```

---

## Tests

```bash
uv run pytest          # full suite
uv run pytest -q       # quiet
uv run pytest --tb=short -q   # matches CI
```

Integration tests spin up a fresh SQLite DB per test run — no external services
or env vars required.

---

## Project layout

```
src/hasl_calendar/
├── app.py          Flask routes (iCal feeds, sync API)
├── scraper.py      HTML parser + sync_to_db + sync_via_api
├── sync_cron.py    Entrypoint for the cron service
├── models.py       SQLAlchemy models (Team, Game)
├── ical.py         iCal feed builder
└── migrate.py      DB migration (run on web service startup)

terraform/          Infrastructure-as-code (see docs/railway.md)
dev/                Local-only helpers (not production)
tests/              Integration tests
```
