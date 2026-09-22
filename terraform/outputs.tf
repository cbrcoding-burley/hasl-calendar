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
  description = "Reminder: generate this token in Railway dashboard → project → Settings → Tokens, scoped to the environment, then export as TF_VAR_railway_ci_token before applying."
  value       = "Railway CI token for '${local.env}' must be generated manually — the provider does not support token creation."
}
