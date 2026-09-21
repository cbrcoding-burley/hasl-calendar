data "github_repository" "this" {
  name = var.github_repo
}

# ── GitHub Actions environment ────────────────────────────────────────────────
# Mirrors the Railway environment. Production is locked to deploy_branch.

resource "github_repository_environment" "this" {
  repository  = data.github_repository.this.name
  environment = local.env

  dynamic "deployment_branch_policy" {
    for_each = local.env == "production" ? [1] : []
    content {
      protected_branches     = false
      custom_branch_policies = true
    }
  }
}

resource "github_repository_environment_deployment_policy" "main_branch" {
  count          = local.env == "production" ? 1 : 0
  repository     = data.github_repository.this.name
  environment    = github_repository_environment.this.environment
  branch_pattern = var.deploy_branch
}

# ── GitHub Actions secrets ────────────────────────────────────────────────────
# These replace every secret you'd otherwise set by hand in the GitHub UI.

resource "github_actions_environment_secret" "railway_token" {
  repository      = data.github_repository.this.name
  environment     = github_repository_environment.this.environment
  secret_name     = "RAILWAY_TOKEN"
  plaintext_value = railway_token.ci.token
}

resource "github_actions_environment_secret" "railway_project_id" {
  repository      = data.github_repository.this.name
  environment     = github_repository_environment.this.environment
  secret_name     = "RAILWAY_PROJECT_ID"
  plaintext_value = railway_project.this.id
}

resource "github_actions_environment_secret" "railway_service_name" {
  repository      = data.github_repository.this.name
  environment     = github_repository_environment.this.environment
  secret_name     = "RAILWAY_SERVICE_NAME"
  plaintext_value = railway_service.web.name
}

resource "github_actions_environment_secret" "railway_cron_service_name" {
  repository      = data.github_repository.this.name
  environment     = github_repository_environment.this.environment
  secret_name     = "RAILWAY_CRON_SERVICE_NAME"
  plaintext_value = railway_service.cron.name
}
