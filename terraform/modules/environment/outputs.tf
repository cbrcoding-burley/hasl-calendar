output "project_id" {
  value = railway_project.this.id
}

output "environment_id" {
  value = railway_environment.this.id
}

output "web_service_id" {
  value = railway_service.web.id
}

output "cron_service_id" {
  value = railway_service.cron.id
}

output "web_domain" {
  value = var.custom_domain != null ? railway_custom_domain.web[0].domain : null
}
