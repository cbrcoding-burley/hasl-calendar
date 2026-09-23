# Infrastructure — Railway via Terraform

## Architecture

```
GitHub (main branch)
    │
    ├─▶ GitHub Actions CI (tests only)
    │
    └─▶ Railway auto-deploy (source_repo connection)
            │
  ┌─────────┴──────────┐
  │                    │
hasl-calendar-server  hasl-calendar-cron
(Web, always-on)      (Cron, 0 */6 * * *)
Flask + gunicorn       python -m hasl_calendar.sync_cron
        │                    │
        │   /sync/* API       │ HTTP (Railway private network)
        └────────────────────┘
        │
   SQLite DB
(volume at /data)
```

One Railway project contains both a `production` and a `staging` environment. Railway deploys each service automatically when code is pushed to `main` — no `railway up` or CI deploy step.

The two environments share the same service definitions but have independent variables and (for `production`) a persistent volume.

**Sync auth** — sync API calls require a short-lived RS256 JWT. The cron service signs tokens with a private key; the web service verifies with the matching public key. See [developers.md](developers.md) for keypair setup.

---

## Terraform structure

```
terraform/
├── versions.tf              # provider pinning + state backend (Railway, Cloudflare)
├── main.tf                  # project, environments, services, variables, custom domain
├── variables.tf             # inputs
├── outputs.tf
└── production.tfvars.example
```

Requires **Terraform >= 1.7** (uses `for_each` on `import` blocks for conditional import).

---

## Prerequisites

- Terraform >= 1.7: `brew install terraform`
- A Railway account and account-level API token (Railway → Settings → Tokens)
- The sync keypair in `.secrets/` (see [developers.md](developers.md))

---

## First-time setup

### 1. Initialize

```bash
cd terraform
terraform init
```

### 2. Export credentials

```bash
export TF_VAR_railway_token="<account-level Railway token>"
export TF_VAR_github_owner="<your-github-username>"
export TF_VAR_sync_public_key="$(cat ../.secrets/public_key.pem)"
export TF_VAR_sync_private_key="$(cat ../.secrets/private_key.pem)"

# If the Railway project already exists, grab the production environment ID from
# Railway dashboard → project Settings → Environments, then:
export TF_VAR_existing_production_environment_id="<env-id>"
# Leave unset (or set to "") for a brand-new project.
```

Optional — if managing a custom domain via Cloudflare:

```bash
export TF_VAR_root_domain="hasl.example.com"
export TF_VAR_cloudflare_zone_id="..."
export TF_VAR_cloudflare_api_token="..."
```

### 3. Plan and apply

```bash
terraform plan
terraform apply
```

For an existing project, Terraform uses `for_each` on the `import` block to conditionally
import the Railway-created production environment rather than trying to create it (which would
fail since it already exists). No manual `terraform import` needed.

### 4. One manual step: cron start command

The Railway Terraform provider doesn't support per-environment start commands, so after the
first apply, set the cron service's start command in the Railway dashboard:

```
python -m hasl_calendar.sync_cron
```

---

## Ongoing deploys

Push to `main` → Railway auto-deploys both services. `railway.toml` runs `migrate.py` +
`seed.py` before starting gunicorn on the web service.

GitHub Actions CI runs tests on every push and PR — it no longer has a deploy step and
doesn't need Railway secrets.

---

## Staging environment

Staging is created alongside production by the same `terraform apply`. To point staging
at a different branch, configure the branch override in the Railway dashboard (the provider
doesn't support per-environment branch overrides).

---

## Resetting the database

The production volume is persistent. To wipe and reseed it:

```bash
# 1. Set the reset flag on the web service
railway variables --service hasl-calendar-server set RESET_DB_ON_START=true

# 2. Trigger a redeploy
railway redeploy --service hasl-calendar-server

# 3. Clear the flag once the deploy completes
railway variables --service hasl-calendar-server delete RESET_DB_ON_START
```

Or do the same via the Railway dashboard: Variables → add `RESET_DB_ON_START=true` →
Deployments → Redeploy → then remove the variable.

---

## State

Local backend by default — state lives in `terraform/terraform.tfstate`. This file contains
sensitive values; never commit it (`.gitignore` covers this).

To migrate to **HCP Terraform** (free, encrypted, no local files):

```bash
# 1. Sign up at app.terraform.io, create an org, run: terraform login
# 2. In versions.tf replace the backend block with:
#      backend "remote" {
#        organization = "<your-hcp-org>"
#        workspaces { name = "hasl-calendar" }
#      }
# 3. terraform init -migrate-state
```

Other free option: Cloudflare R2 (S3-compatible backend, 10 GB free, no egress fees).

---

## Provider docs

- Railway: https://registry.terraform.io/providers/terraform-community-providers/railway/latest/docs
- Cloudflare: https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs
