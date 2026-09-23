locals {
  env = terraform.workspace
  domain = (
    var.root_domain != "" && local.env == "production"
    ? var.root_domain
    : var.root_domain != ""
    ? "${local.env}.${var.root_domain}"
    : null
  )
}

module "environment" {
  source = "./modules/environment"

  env_name                = local.env
  existing_environment_id = var.existing_environment_id
  github_repo             = var.github_repo
  deploy_branch           = var.deploy_branch
  sync_public_key         = var.sync_public_key
  sync_private_key        = var.sync_private_key
  railway_ci_token        = var.railway_ci_token
  custom_domain           = local.domain
  cloudflare_zone_id      = var.cloudflare_zone_id != "" ? var.cloudflare_zone_id : null
}

# ── State migration ───────────────────────────────────────────────────────────
# These moved blocks handle renaming existing state addresses into the module.
# Safe to remove after the first successful terraform apply on each workspace.

moved {
  from = railway_project.this
  to   = module.environment.railway_project.this
}

moved {
  from = railway_environment.this
  to   = module.environment.railway_environment.this
}

moved {
  from = railway_service.web
  to   = module.environment.railway_service.web
}

moved {
  from = railway_service.cron
  to   = module.environment.railway_service.cron
}

moved {
  from = railway_variable.web_database_url
  to   = module.environment.railway_variable.web_database_url
}

moved {
  from = railway_variable.web_sync_public_key
  to   = module.environment.railway_variable.web_sync_public_key
}

moved {
  from = railway_variable.cron_sync_private_key
  to   = module.environment.railway_variable.cron_sync_private_key
}

moved {
  from = railway_variable.cron_calendar_url
  to   = module.environment.railway_variable.cron_calendar_url
}

moved {
  from = github_repository_environment.this
  to   = module.environment.github_repository_environment.this
}

moved {
  from = github_repository_environment_deployment_policy.main_branch
  to   = module.environment.github_repository_environment_deployment_policy.this
}

moved {
  from = github_actions_environment_secret.railway_token
  to   = module.environment.github_actions_environment_secret.railway_token
}

moved {
  from = github_actions_environment_secret.railway_project_id
  to   = module.environment.github_actions_environment_secret.railway_project_id
}

moved {
  from = github_actions_environment_secret.railway_service_name
  to   = module.environment.github_actions_environment_secret.railway_service_name
}

moved {
  from = github_actions_environment_secret.railway_cron_service_name
  to   = module.environment.github_actions_environment_secret.railway_cron_service_name
}
