variable "railway_token" {
  description = "Railway account-level API token. Set via RAILWAY_TOKEN env var — do not put in tfvars."
  type        = string
  sensitive   = true
}

variable "github_token" {
  description = "GitHub PAT with repo + secrets scopes. Set via GITHUB_TOKEN env var — do not put in tfvars."
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "GitHub username or org that owns the repo (e.g. 'christianreynolds')."
  type        = string
}

variable "github_repo" {
  description = "Repository name without the owner prefix."
  type        = string
  default     = "hasl-calendar"
}

variable "sync_public_key" {
  description = "RSA public key PEM — verifies sync requests in the web service."
  type        = string
  sensitive   = true
}

variable "sync_private_key" {
  description = "RSA private key PEM — signs sync requests in the cron service."
  type        = string
  sensitive   = true
}

variable "deploy_branch" {
  description = "Git branch that the GitHub Actions environment is locked to."
  type        = string
  default     = "main"
}

variable "railway_ci_token" {
  description = "Environment-scoped Railway token for CI deploys. Generate in Railway dashboard → project → Settings → Tokens, scoped to this environment. Set via TF_VAR_railway_ci_token."
  type        = string
  sensitive   = true
}

variable "existing_environment_id" {
  description = "ID of an auto-created Railway environment to import (production only). Railway auto-creates 'production' on project creation; passing its ID here lets Terraform import rather than try to create it. Leave empty for new environments."
  type        = string
  default     = ""
}

variable "root_domain" {
  description = "Apex domain (e.g. 'example.com'). Production gets the apex; other envs get '<env>.example.com'. Empty string disables domain management."
  type        = string
  default     = ""
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for DNS record creation. Empty string disables DNS management."
  type        = string
  default     = ""
  sensitive   = true
}
