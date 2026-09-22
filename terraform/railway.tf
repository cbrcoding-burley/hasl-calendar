locals {
  env = "production" # "production" | "staging" | ...

  # Production keeps the canonical name; other workspaces get a suffix so they
  # live as distinct Railway projects and don't collide.
  project_name = local.env == "production" ? "hasl-calendar" : "hasl-calendar-${local.env}"
}

# ── Project ───────────────────────────────────────────────────────────────────
# One Railway project per workspace. Production should be imported (see docs/railway.md);
# staging and any future environments are created fresh.

resource "railway_project" "this" {
  name = local.project_name
}

# ── Environment ───────────────────────────────────────────────────────────────
# Railway auto-creates a "production" environment when a project is first made.
# For the production workspace, import that environment (see docs/railway.md).
# For staging, Terraform creates it from scratch.

resource "railway_environment" "this" {
  name       = local.env
  project_id = railway_project.this.id
}

# ── Services ──────────────────────────────────────────────────────────────────

resource "railway_service" "web" {
  name       = "hasl-calendar-server"
  project_id = railway_project.this.id

  # Volume is a nested block on the service — no separate railway_volume resource.
  volume = {
    mount_path = "/data"
    name       = "data"
  }
}

resource "railway_service" "cron" {
  name          = "hasl-calendar-cron"
  project_id    = railway_project.this.id
  cron_schedule = "0 */6 * * *"
  # start_command is not a provider attribute — set it in the Railway dashboard
  # or via railway.toml service config after first deploy.
}

# ── Web service variables ─────────────────────────────────────────────────────

resource "railway_variable" "web_database_url" {
  environment_id = railway_environment.this.id
  service_id     = railway_service.web.id
  name           = "DATABASE_URL"
  value          = "sqlite:////data/hasl.db"
}

resource "railway_variable" "web_sync_public_key" {
  environment_id = railway_environment.this.id
  service_id     = railway_service.web.id
  name           = "SYNC_PUBLIC_KEY"
  value          = var.sync_public_key
}

# ── Cron service variables ────────────────────────────────────────────────────

resource "railway_variable" "cron_sync_private_key" {
  environment_id = railway_environment.this.id
  service_id     = railway_service.cron.id
  name           = "SYNC_PRIVATE_KEY"
  value          = var.sync_private_key
}

resource "railway_variable" "cron_calendar_url" {
  environment_id = railway_environment.this.id
  service_id     = railway_service.cron.id
  name           = "HASL_CALENDAR_URL"

  # Railway private network: cron → web without leaving Railway's internal network.
  value = "http://${railway_service.web.name}.railway.internal:8080"
}
