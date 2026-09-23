# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run dev server (auto-reload)
uv run flask --app hasl_calendar.app run --debug

# Run production-like server
uv run gunicorn 'hasl_calendar.app:app' --bind 0.0.0.0:8000 --workers 2

# Run tests
uv run pytest
uv run pytest --tb=short -q   # CI-style

# One-off schedule sync (requires a running web service)
export HASL_CALENDAR_URL="http://localhost:5000"
export SYNC_PRIVATE_KEY="$(cat .secrets/private_key.pem)"
uv run python -m hasl_calendar.sync_cron

# Seed local DB directly (bypasses sync API)
uv run python seed.py
```

## Architecture

Two services, one repo:

| Service | Role |
|---|---|
| `hasl-calendar` (web) | Flask app — serves iCal feeds, owns the SQLite DB, exposes authenticated sync API |
| `hasl-calendar-cron` | Runs every 6h — scrapes HASL schedule, pushes changes to web service via HTTP |

**The cron service never touches the database directly.** It calls the web service's sync API (`/sync/state`, `/sync/upsert`, `/sync/delete`). On Railway, cron reaches web over the private network (`hasl-calendar.railway.internal:8080`).

**Sync auth** — sync endpoints require an RS256 JWT. The cron service signs tokens with a private key (`SYNC_PRIVATE_KEY`); the web service verifies with the matching public key (`SYNC_PUBLIC_KEY`). Tokens expire after 5 minutes. Keys live in `.secrets/` (gitignored); use separate keypairs per environment.

**DB** — SQLite at `sqlite:///hasl.db` locally, `sqlite:////data/hasl.db` in production (Railway persistent volume mounted at `/data` on the web service only).

**Deploy flow** — Push to `main` → GitHub Actions runs tests → Railway auto-deploys both services. `railway.toml` runs `migrate.py` + `seed.py` as a pre-deploy command before starting gunicorn.

## Key source files

```
src/hasl_calendar/
├── app.py         Flask routes — iCal feeds + sync API
├── scraper.py     HTML parser (BeautifulSoup/lxml) + sync_to_db + sync_via_api
├── sync_cron.py   Cron service entrypoint
├── models.py      SQLAlchemy models: Team (PK: slug), Game (PK: sha1 of date+time+teams)
├── ical.py        Builds iCal feed bytes from Team + Game records
└── migrate.py     DB schema migration, run on every web service startup
```

## Infrastructure (Terraform)

`terraform/` manages all Railway infrastructure: one project, `production` + `staging` environments, and both services. GitHub CI only runs tests — Railway auto-deploys on push to `main` via its GitHub source connection.

```bash
cd terraform
terraform init
export TF_VAR_railway_token="..."
export TF_VAR_github_owner="christianreynolds"
export TF_VAR_sync_public_key="$(cat ../.secrets/public_key.pem)"
export TF_VAR_sync_private_key="$(cat ../.secrets/private_key.pem)"
# If the Railway project already exists, also set:
export TF_VAR_existing_production_environment_id="<id from Railway dashboard>"
terraform apply
```

See `docs/railway.md` for full setup, import instructions, and DB reset procedure.

**Known provider quirk** — `railway_service.web` has `lifecycle { ignore_changes = [volume] }` to work around a Railway Terraform provider bug where the volume attribute reads back as null after creation, causing a spurious drift error. The volume is created correctly in Railway.

State is local by default (`terraform/terraform.tfstate`). Never commit state files — they contain secrets.
