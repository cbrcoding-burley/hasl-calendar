# Railway Infrastructure Setup

This is a one-time manual bootstrap required before CI-driven deploys can work.
Subsequent deploys happen automatically via GitHub Actions on push to `main`.

> **Note:** This manual setup is a known limitation of Railway. Full Terraform
> automation is planned — see future work below.

## How Railway environments work

Railway has first-class environments (e.g. `production`, `staging`) built into a project.
The same services run in each environment with separate config, volumes, and deploy history.
You don't create separate services per environment — you create separate Railway environments,
each with its own scoped token.

## Prerequisites

- A Railway account at [railway.app](https://railway.app)
- The Railway CLI installed: `npm install -g @railway/cli`
- Keys generated in `.secrets/` (run `uv run python -c "from scripts.gen_keys import main; main()"` or see `.secrets/` — keys should already exist)

## Services

This project has two Railway services:

| Service | Type | Purpose |
|---|---|---|
| `hasl-calendar` | Web | Serves iCal feeds, exposes sync API |
| `hasl-calendar-cron` | Cron | Scrapes HASL schedule, calls sync API |

---

## Web service setup (`hasl-calendar`)

### 1. Create the project and service

In the Railway dashboard:
- New Project → Empty Project
- Add Service → Empty Service, name it `hasl-calendar`

Railway creates a `production` environment by default.

### 2. Add a persistent volume

In the service → **Volumes** → **Add Volume** (do this per Railway environment):
- Mount path: `/data`

### 3. Set environment variables

In the service → **Variables** (do this per Railway environment):

| Variable | Value |
|---|---|
| `DATABASE_URL` | `sqlite:////data/hasl.db` |
| `SYNC_PUBLIC_KEY` | Contents of `.secrets/public_key.pem` |

### 4. Grab the credentials

You'll need these for GitHub secrets:

- **Project ID**: Railway dashboard → project → Settings → copy the project UUID
- **Service name**: `hasl-calendar`
- **Railway token**: Railway dashboard → project → Settings → Tokens → New Token
  — scope it to the specific Railway environment (e.g. `production`), not the whole project

### 5. Add GitHub secrets

In the GitHub repo → **Settings** → **Environments** → create a `production` environment, then add:

| Secret | Value |
|---|---|
| `RAILWAY_TOKEN` | Token scoped to the Railway `production` environment |
| `RAILWAY_PROJECT_ID` | Project UUID (same across all GitHub environments) |
| `RAILWAY_SERVICE_NAME` | `hasl-calendar` (same across all GitHub environments) |

Also set a branch protection rule on the `production` environment: only allow deployments from `main`.

### 6. Disable Railway's native GitHub auto-deploy

In the service → **Settings** → **Source** → disconnect or disable auto-deploy.
CI is the only deploy trigger; Railway's native integration bypasses the test gate.

---

## Cron service setup (`hasl-calendar-cron`)

### 1. Create the cron service

In the Railway dashboard (same project):
- Add Service → Empty Service, name it `hasl-calendar-cron`
- In the service → **Settings** → **Service Type** → set to **Cron**
- Set cron schedule: `0 */6 * * *`
- Set start command: `python -m hasl_calendar.sync_cron`

### 2. Set environment variables

In the cron service → **Variables**:

| Variable | Value |
|---|---|
| `SYNC_PRIVATE_KEY` | Contents of `.secrets/private_key.pem` |
| `HASL_CALENDAR_URL` | `http://hasl-calendar.railway.internal:8080` |

> The `railway.internal` hostname is Railway's private network — the cron service
> reaches the web service without going over the public internet.

### 3. Deploy the cron service

The cron service deploys from the same repo as the web service. In the cron service
→ **Settings** → **Source** → connect to the same GitHub repo and branch (`main`).

---

## Adding a staging environment

1. In Railway dashboard → Environments → New Environment (e.g. `staging`)
2. Repeat web service setup (volume, env vars) for the staging environment
3. Generate a new Railway token scoped to the `staging` environment
4. In GitHub → Settings → Environments → create a `staging` environment with:
   - `RAILWAY_TOKEN` — the staging-scoped Railway token
   - `RAILWAY_PROJECT_ID` — same UUID as production
   - `RAILWAY_SERVICE_NAME` — same name as production (`hasl-calendar`)
5. Add a deploy job to `.github/workflows/ci.yml` targeting `environment: staging`

---

## Future work: Terraform

The manual bootstrap steps above are tracked for Terraform automation using the
[Railway Terraform provider](https://registry.terraform.io/providers/railwayapp/railway/latest)
combined with the GitHub provider to wire up secrets automatically.
