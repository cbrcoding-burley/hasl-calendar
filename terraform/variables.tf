variable "railway_token" {
  description = "Railway account-level API token. Set via RAILWAY_TOKEN env var — do not put in tfvars."
  type        = string
  sensitive   = true
}

variable "github_token" {
  description = "GitHub personal access token. Set via TF_VAR_github_token — do not put in tfvars."
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

variable "enable_staging" {
  description = "Whether to create the staging environment and its resources."
  type        = bool
  default     = false
}

variable "root_domain" {
  description = "Apex domain to assign to the production web service (e.g. 'example.com'). Empty string disables domain management."
  type        = string
  default     = ""
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token with Edit Zone DNS permissions. Set via TF_VAR_cloudflare_api_token."
  type        = string
  default     = ""
  sensitive   = true
}
