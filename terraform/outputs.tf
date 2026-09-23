output "project_id" {
  description = "Railway project ID."
  value       = module.environment.project_id
}

output "environment_id" {
  description = "Railway environment ID."
  value       = module.environment.environment_id
}

output "web_service_id" {
  description = "Railway web service ID."
  value       = module.environment.web_service_id
}

output "cron_service_id" {
  description = "Railway cron service ID."
  value       = module.environment.cron_service_id
}

output "web_domain" {
  description = "Custom domain assigned to the web service, if any."
  value       = module.environment.web_domain
}
