locals {
  project_name = var.env_name == "production" ? "hasl-calendar" : "hasl-calendar-${var.env_name}"
}

# ── Project ───────────────────────────────────────────────────────────────────

resource "railway_project" "this" {
  name = local.project_name
}

# ── Environment ───────────────────────────────────────────────────────────────
# Railway auto-creates a "production" environment on project creation.
# For production, import it via the existing_environment_id variable instead of
# trying to create it (which would fail). For new environments, leave the
# variable empty and Terraform creates it normally.

import {
  for_each = var.existing_environment_id != "" ? { main = var.existing_environment_id } : {}
  to       = railway_environment.this
  id       = "${railway_project.this.id}:${each.value}"
}

resource "railway_environment" "this" {
  name       = var.env_name
  project_id = railway_project.this.id
}

# ── Services ──────────────────────────────────────────────────────────────────

resource "railway_service" "web" {
  name       = "hasl-calendar-server"
  project_id = railway_project.this.id

  volume = {
    mount_path = "/data"
    name       = "data"
  }

  # Provider bug: after creating the volume, the provider's Read returns null for
  # the volume attribute, causing Terraform to report an inconsistency. The volume
  # IS created in Railway — ignore drift on it to avoid the spurious error.
  lifecycle {
    ignore_changes = [volume]
  }
}

resource "railway_service" "cron" {
  name          = "hasl-calendar-cron"
  project_id    = railway_project.this.id
  cron_schedule = "0 */6 * * *"
  # start_command is not a provider attribute — set it in the Railway dashboard
  # or via railway.toml after first deploy: python -m hasl_calendar.sync_cron
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
  value          = "http://${railway_service.web.name}.railway.internal:8080"
}

# ── Custom domain (optional) ──────────────────────────────────────────────────

resource "railway_custom_domain" "web" {
  count          = var.custom_domain != null ? 1 : 0
  domain         = var.custom_domain
  service_id     = railway_service.web.id
  environment_id = railway_environment.this.id
}

resource "cloudflare_record" "web" {
  count   = var.custom_domain != null && var.cloudflare_zone_id != null ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.custom_domain
  value   = railway_custom_domain.web[0].dns_record_value
  type    = "CNAME"
  proxied = true
}

# ── GitHub Actions environment + secrets ─────────────────────────────────────

resource "github_repository_environment" "this" {
  repository  = var.github_repo
  environment = var.env_name

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "this" {
  repository     = var.github_repo
  environment    = github_repository_environment.this.environment
  branch_pattern = var.deploy_branch
}

resource "github_actions_environment_secret" "railway_token" {
  repository      = var.github_repo
  environment     = github_repository_environment.this.environment
  secret_name     = "RAILWAY_TOKEN"
  plaintext_value = var.railway_ci_token
}

resource "github_actions_environment_secret" "railway_project_id" {
  repository      = var.github_repo
  environment     = github_repository_environment.this.environment
  secret_name     = "RAILWAY_PROJECT_ID"
  plaintext_value = railway_project.this.id
}

resource "github_actions_environment_secret" "railway_service_name" {
  repository      = var.github_repo
  environment     = github_repository_environment.this.environment
  secret_name     = "RAILWAY_SERVICE_NAME"
  plaintext_value = railway_service.web.name
}

resource "github_actions_environment_secret" "railway_cron_service_name" {
  repository      = var.github_repo
  environment     = github_repository_environment.this.environment
  secret_name     = "RAILWAY_CRON_SERVICE_NAME"
  plaintext_value = railway_service.cron.name
}
