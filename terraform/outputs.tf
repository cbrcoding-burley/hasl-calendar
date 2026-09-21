output "project_id" {
  description = "Railway project ID — save this; it's needed if you ever import into a fresh state."
  value       = railway_project.this.id
}

output "environment_id" {
  description = "Railway environment ID."
  value       = railway_environment.this.id
}

output "web_service_id" {
  description = "Railway web service ID."
  value       = railway_service.web.id
}

output "cron_service_id" {
  description = "Railway cron service ID."
  value       = railway_service.cron.id
}

output "ci_token_hint" {
  description = "Reminder: the CI token is written directly to GitHub Actions secrets — you don't need to copy it."
  value       = "Railway token for '${local.env}' is managed in GitHub → Environments → ${local.env} → RAILWAY_TOKEN"
}
