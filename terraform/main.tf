locals {
  environments = {
    production = railway_environment.production.id
    staging    = railway_environment.staging.id
  }
}

# ── Project ───────────────────────────────────────────────────────────────────

resource "railway_project" "this" {
  name = "hasl-calendar"
}

# ── Environments ──────────────────────────────────────────────────────────────
# Railway auto-creates a "production" environment on project creation.
# Pass existing_production_environment_id to import it instead of creating it.

import {
  for_each = var.existing_production_environment_id != "" ? { main = var.existing_production_environment_id } : {}
  to       = railway_environment.production
  id       = "${railway_project.this.id}:${each.value}"
}

resource "railway_environment" "production" {
  name       = "production"
  project_id = railway_project.this.id
}

resource "railway_environment" "staging" {
  name       = "staging"
  project_id = railway_project.this.id
}

# ── Services ──────────────────────────────────────────────────────────────────
# Services belong to the project; Railway deploys them per environment.
# source_repo_branch sets the default deploy branch (production → main).
# Per-environment branch overrides (e.g. staging → staging branch) are
# configured in the Railway dashboard — the provider doesn't support them.

resource "railway_service" "web" {
  name               = "hasl-calendar-server"
  project_id         = railway_project.this.id
  source_repo        = "${var.github_owner}/${var.github_repo}"
  source_repo_branch = "main"

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
  cron_schedule      = "0 */6 * * *"
  source_repo        = "${var.github_owner}/${var.github_repo}"
  source_repo_branch = "main"
  # start_command: set in Railway dashboard — python -m hasl_calendar.sync_cron
}

# ── Variables (applied to all managed environments) ───────────────────────────

resource "railway_variable" "web_database_url" {
  for_each       = local.environments
  environment_id = each.value
  service_id     = railway_service.web.id
  name           = "DATABASE_URL"
  value          = "sqlite:////data/hasl.db"
}

resource "railway_variable" "web_sync_public_key" {
  for_each       = local.environments
  environment_id = each.value
  service_id     = railway_service.web.id
  name           = "SYNC_PUBLIC_KEY"
  value          = var.sync_public_key
}

resource "railway_variable" "cron_sync_private_key" {
  for_each       = local.environments
  environment_id = each.value
  service_id     = railway_service.cron.id
  name           = "SYNC_PRIVATE_KEY"
  value          = var.sync_private_key
}

resource "railway_variable" "cron_calendar_url" {
  for_each       = local.environments
  environment_id = each.value
  service_id     = railway_service.cron.id
  name           = "HASL_CALENDAR_URL"
  value          = "http://${railway_service.web.name}.railway.internal:8080"
}

# ── Custom domain (optional, production only) ─────────────────────────────────

resource "railway_custom_domain" "web" {
  count          = var.root_domain != "" ? 1 : 0
  domain         = var.root_domain
  service_id     = railway_service.web.id
  environment_id = railway_environment.production.id
}

resource "cloudflare_record" "web" {
  count   = var.root_domain != "" && var.cloudflare_zone_id != "" ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.root_domain
  value   = railway_custom_domain.web[0].dns_record_value
  type    = "CNAME"
  proxied = true
}
