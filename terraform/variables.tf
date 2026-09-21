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
  description = "Git branch that the production GitHub environment is locked to."
  type        = string
  default     = "main"
}
