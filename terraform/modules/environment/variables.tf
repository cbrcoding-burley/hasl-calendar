variable "env_name" {
  description = "Environment name: 'production', 'staging', etc."
  type        = string
}

variable "existing_environment_id" {
  description = "ID of an auto-created Railway environment to import instead of creating. Required for production (Railway auto-creates it on project creation). Leave empty for new environments."
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "Repository name without the owner prefix."
  type        = string
  default     = "hasl-calendar"
}

variable "github_environment" {
  description = "GitHub Actions environment name. Defaults to env_name. Override when the workspace name differs from the desired GitHub environment name."
  type        = string
  default     = null
}

variable "deploy_branch" {
  description = "Git branch the GitHub Actions environment is locked to."
  type        = string
  default     = "main"
}

variable "sync_public_key" {
  type      = string
  sensitive = true
}

variable "sync_private_key" {
  type      = string
  sensitive = true
}

variable "railway_ci_token" {
  description = "Environment-scoped Railway token for CI. Generate in Railway dashboard → project → Settings → Tokens."
  type        = string
  sensitive   = true
}

variable "custom_domain" {
  description = "Full domain to assign to the web service (e.g. 'example.com' or 'staging.example.com'). Null skips domain creation."
  type        = string
  default     = null
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for DNS record creation. Null skips DNS record creation."
  type        = string
  default     = null
}
