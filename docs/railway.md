# Infrastructure — Railway via Terraform

## Architecture

```
GitHub (main branch)
    │
    └─▶ GitHub Actions CI
            │  tests pass
            └─▶ railway up (web + cron)
                    │
          ┌─────────┴──────────┐
          │                    │
   hasl-calendar        hasl-calendar-cron
   (Web, always-on)     (Cron, 0 */6 * * *)
   Flask + gunicorn      python -m hasl_calendar.sync_cron
          │                    │
          │   /sync/* API       │ HTTP (Railway private network)
          └────────────────────┘
          │
     SQLite DB
  (volume at /data)
```

**hasl-calendar** serves iCal feeds at `/calendar/<team>.ics` and exposes an
authenticated sync API. It owns the database.

**hasl-calendar-cron** runs every 6 hours, scrapes the HASL schedule page, and
pushes changes to the web service via the sync API. It never touches the DB
directly. On Railway the two services communicate over the private network
(`hasl-calendar.railway.internal:8080`) without going through the public internet.

**Sync auth** — sync API calls require a short-lived RS256 JWT. The cron service
signs tokens with a private key; the web service verifies them with the matching
public key. See [developers.md](developers.md) for keypair setup.

---

All Railway and GitHub Actions infrastructure is managed with Terraform. The goal
is zero pointing-and-clicking: `terraform apply` does everything.

## Prerequisites

- Terraform >= 1.6: `brew install terraform`
- A Railway account and an account-level API token (Railway dashboard → Settings → Tokens)
- A GitHub PAT with scopes: `repo`, `admin:repo_hook`, `secrets`
- The sync keypair already generated in `.secrets/`

## Structure

```
terraform/
├── versions.tf              # provider pinning + state backend
├── main.tf                  # Railway project, environment, services, volumes, variables, CI token
├── github.tf                # GitHub Actions environment + all secrets
├── variables.tf             # inputs
├── outputs.tf
├── production.tfvars.example
└── staging.tfvars.example
```

One Terraform workspace = one Railway project + one GitHub Actions environment.

## Environments

| Workspace    | Railway project        | GitHub Actions env |
|---|---|---|
| `production` | `hasl-calendar`        | `production`       |
| `staging`    | `hasl-calendar-staging`| `staging`          |

Add more environments by creating a new workspace and running apply.

---

## First-time setup: production

Production already exists — Terraform needs to import the live resources instead
of trying to create them.

### 1. Initialize and select workspace

```bash
cd terraform
terraform init
terraform workspace new production   # or: terraform workspace select production
```

### 2. Export credentials

```bash
export TF_VAR_railway_token="<account-level Railway token>"
export TF_VAR_github_token="ghp_..."
export TF_VAR_sync_public_key="$(cat ../.secrets/public_key.pem)"
export TF_VAR_sync_private_key="$(cat ../.secrets/private_key.pem)"
```

### 3. Import existing Railway resources

Grab the IDs from the Railway dashboard (project Settings → IDs, or via `railway status`):

```bash
# Railway project
terraform import railway_project.this <PROJECT_ID>

# Railway auto-creates a "production" environment on project creation.
# If you don't import it first, apply will fail with "environment already exists".
terraform import railway_environment.this <PROJECT_ID>:<ENVIRONMENT_ID>

# Services
terraform import railway_service.web  <PROJECT_ID>:<WEB_SERVICE_ID>
terraform import railway_service.cron <PROJECT_ID>:<CRON_SERVICE_ID>

# Variables (only needed if you want Terraform to own existing values;
# a plain apply will create/upsert them regardless)
```

> **Note:** Volumes are managed as a nested block on `railway_service.web` rather
> than as a separate import target. A `lifecycle { ignore_changes = [volume] }`
> guard works around a provider bug where the volume read returns null after creation
> — the volume is created in Railway but Terraform would otherwise error.

### 4. Apply

```bash
terraform plan -var-file=production.tfvars   # review — should show no destructive changes
terraform apply -var-file=production.tfvars
```

This writes all four GitHub Actions secrets to the `production` environment automatically.

---

## New environment: staging (or any other)

No imports needed — everything is created from scratch.

```bash
cd terraform
terraform workspace new staging

export TF_VAR_railway_token="..."
export TF_VAR_github_token="..."
export TF_VAR_sync_public_key="$(cat ../.secrets/public_key.pem)"   # or staging-specific keys
export TF_VAR_sync_private_key="$(cat ../.secrets/private_key.pem)"

terraform apply -var-file=staging.tfvars
```

Terraform creates:
- A new Railway project `hasl-calendar-staging`
- A `staging` environment inside it
- Both services (web + cron) with all variables and the persistent volume
- A `staging` GitHub Actions environment locked to the deploy branch
- All four `RAILWAY_*` secrets written directly to GitHub

---

## Services

| Service | Type | Start command |
|---|---|---|
| `hasl-calendar` | Web | `railway.toml` → gunicorn |
| `hasl-calendar-cron` | Cron (`0 */6 * * *`) | `python -m hasl_calendar.sync_cron` |

The cron service's internal URL for the `HASL_CALENDAR_URL` variable is computed by
Terraform: `http://hasl-calendar.railway.internal:8080`. This uses Railway's private
network so cron → web traffic never leaves Railway's infrastructure.

---

## State

Local backend by default — state files live in `terraform/terraform.tfstate.d/<workspace>/`.
These contain sensitive values; keep them off shared drives and never commit them (`.gitignore` covers this).

To migrate to **HCP Terraform** (free, encrypted, no local files):

```bash
# 1. Sign up at app.terraform.io, create an org, run: terraform login
# 2. In versions.tf replace the backend block with:
#      backend "remote" {
#        organization = "<your-hcp-org>"
#        workspaces { prefix = "hasl-calendar-" }
#      }
# 3. terraform init -migrate-state
```

Other free options: Cloudflare R2 (S3-compatible backend, 10 GB free, no egress fees).

---

## Provider docs

- Railway: https://registry.terraform.io/providers/railwayapp/railway/latest/docs
- GitHub: https://registry.terraform.io/providers/integrations/github/latest/docs
