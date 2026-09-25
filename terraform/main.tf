locals {
  production_environment_id = railway_project.this.default_environment.id
  staging_environment_id    = var.enable_staging ? railway_environment.staging[0].id : ""
}

# ── Project ───────────────────────────────────────────────────────────────────
# Railway auto-creates a "production" environment on project creation.
# Its ID is exposed as default_environment.id — we reference that in locals
# rather than managing it as a separate resource, because Terraform can't
# import a resource whose ID depends on a computed value at plan time.

resource "railway_project" "this" {
  name           = "hasl-calendar"
  has_pr_deploys = true

  default_environment = {
    name = "production"
  }
}

# ── Environments ──────────────────────────────────────────────────────────────

resource "railway_environment" "staging" {
  count      = var.enable_staging ? 1 : 0
  name       = "staging"
  project_id = railway_project.this.id
}

# ── Services ──────────────────────────────────────────────────────────────────
# After a fresh apply, configure these manually in the Railway dashboard
# (provider doesn't support them):
#   - auto-deploy on push: enable per environment under service → Settings → Deploy
#   - wait for CI: enable under service → Settings → Deploy → "Wait for CI checks"
#   - GitHub repo permissions: grant Railway access under GitHub → Settings → Applications
#   - per-environment branch overrides (e.g. staging → staging branch)
#   - start commands for services that need them (see comments below)

resource "railway_service" "web" {
  name               = "hasl-calendar-server"
  project_id         = railway_project.this.id
  source_repo        = "${var.github_owner}/${var.github_repo}"
  source_repo_branch = "main"
  root_directory     = "/"
  config_path        = "railway.toml"

  volume = {
    mount_path = "/data"
    name       = "data"
  }

  # Provider bug: after creating the volume, the provider's Read returns null,
  # causing a spurious inconsistency error. Volume IS created in Railway.
  lifecycle {
    ignore_changes = [volume]
  }
}

resource "railway_service" "cron" {
  name               = "hasl-calendar-cron"
  project_id         = railway_project.this.id
  cron_schedule      = "*/15 * * * *"
  source_repo        = "${var.github_owner}/${var.github_repo}"
  source_repo_branch = "main"
  root_directory     = "/"
  config_path        = "railway-cron.toml"
}

# ── Variables ─────────────────────────────────────────────────────────────────
# Staging blocks depend_on production blocks because the Railway provider
# triggers a service redeploy after each variable write; parallel creates for
# the same service cause a "deployment already in progress" error.

resource "railway_variable" "web_database_url_production" {
  depends_on     = [railway_service.web, railway_service.cron]
  environment_id = local.production_environment_id
  service_id     = railway_service.web.id
  name           = "DATABASE_URL"
  value          = "sqlite:////data/hasl.db"
}

resource "railway_variable" "web_sync_public_key_production" {
  depends_on     = [railway_variable.web_database_url_production]
  environment_id = local.production_environment_id
  service_id     = railway_service.web.id
  name           = "SYNC_PUBLIC_KEY"
  value          = var.sync_public_key
}

resource "railway_variable" "cron_sync_private_key_production" {
  depends_on     = [railway_variable.web_sync_public_key_production]
  environment_id = local.production_environment_id
  service_id     = railway_service.cron.id
  name           = "SYNC_PRIVATE_KEY"
  value          = var.sync_private_key
}

resource "railway_variable" "cron_calendar_url_production" {
  depends_on     = [railway_variable.cron_sync_private_key_production]
  environment_id = local.production_environment_id
  service_id     = railway_service.cron.id
  name           = "HASL_CALENDAR_URL"
  value          = "http://${railway_service.web.name}.railway.internal:8080"
}

resource "railway_variable" "web_database_url_staging" {
  count          = var.enable_staging ? 1 : 0
  depends_on     = [railway_variable.cron_calendar_url_production]
  environment_id = local.staging_environment_id
  service_id     = railway_service.web.id
  name           = "DATABASE_URL"
  value          = "sqlite:///hasl.db"
}

resource "railway_variable" "web_sync_public_key_staging" {
  count          = var.enable_staging ? 1 : 0
  depends_on     = [railway_variable.web_database_url_staging]
  environment_id = local.staging_environment_id
  service_id     = railway_service.web.id
  name           = "SYNC_PUBLIC_KEY"
  value          = var.sync_public_key
}

resource "railway_variable" "cron_sync_private_key_staging" {
  count          = var.enable_staging ? 1 : 0
  depends_on     = [railway_variable.web_sync_public_key_staging]
  environment_id = local.staging_environment_id
  service_id     = railway_service.cron.id
  name           = "SYNC_PRIVATE_KEY"
  value          = var.sync_private_key
}

resource "railway_variable" "cron_calendar_url_staging" {
  count          = var.enable_staging ? 1 : 0
  depends_on     = [railway_variable.cron_sync_private_key_staging]
  environment_id = local.staging_environment_id
  service_id     = railway_service.cron.id
  name           = "HASL_CALENDAR_URL"
  value          = "http://${railway_service.web.name}.railway.internal:8080"
}

# ── Custom domain (optional, production only) ─────────────────────────────────

data "cloudflare_zone" "this" {
  count = var.root_domain != "" ? 1 : 0
  name  = var.root_domain
}

resource "railway_custom_domain" "web" {
  count          = var.root_domain != "" ? 1 : 0
  domain         = var.root_domain
  service_id     = railway_service.web.id
  environment_id = local.production_environment_id
}

resource "railway_custom_domain" "staging" {
  count          = var.enable_staging && var.root_domain != "" ? 1 : 0
  domain         = "staging.${var.root_domain}"
  service_id     = railway_service.web.id
  environment_id = local.staging_environment_id
}
