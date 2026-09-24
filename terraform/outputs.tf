output "project_id" {
  description = "Railway project ID."
  value       = railway_project.this.id
}

output "production_environment_id" {
  description = "Railway production environment ID (auto-created by Railway)."
  value       = railway_project.this.default_environment
}

output "staging_environment_id" {
  description = "Railway staging environment ID."
  value       = railway_environment.staging.id
}

output "web_service_id" {
  description = "Railway web service ID."
  value       = railway_service.web.id
}

output "cron_service_id" {
  description = "Railway cron service ID."
  value       = railway_service.cron.id
}

output "web_domain" {
  description = "Custom domain assigned to the production web service, if any."
  value       = var.root_domain != "" ? railway_custom_domain.web[0].domain : null
}
