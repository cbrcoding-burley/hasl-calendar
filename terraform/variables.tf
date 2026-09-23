variable "railway_token" {
  description = "Railway account-level API token. Set via RAILWAY_TOKEN env var — do not put in tfvars."
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

variable "existing_production_environment_id" {
  description = "ID of Railway's auto-created 'production' environment. Get from Railway dashboard → project Settings → Environments. Leave empty for a brand-new project."
  type        = string
  default     = ""
}

variable "root_domain" {
  description = "Apex domain to assign to the production web service (e.g. 'example.com'). Empty string disables domain management."
  type        = string
  default     = ""
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for DNS record creation. Empty string disables DNS management."
  type        = string
  default     = ""
  sensitive   = true
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token with Edit Zone DNS permissions. Set via TF_VAR_cloudflare_api_token."
  type        = string
  default     = ""
  sensitive   = true
}
