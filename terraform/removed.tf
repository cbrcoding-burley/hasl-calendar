# Forget stale Railway state after project was deleted in the UI.
# Apply once, then delete this file and apply again to recreate everything.

removed {
  from = railway_project.this
  lifecycle { destroy = false }
}

removed {
  from = railway_environment.production
  lifecycle { destroy = false }
}

removed {
  from = railway_environment.staging
  lifecycle { destroy = false }
}

removed {
  from = railway_service.web
  lifecycle { destroy = false }
}

removed {
  from = railway_service.cron
  lifecycle { destroy = false }
}

removed {
  from = railway_variable.web_database_url["production"]
  lifecycle { destroy = false }
}

removed {
  from = railway_variable.web_database_url["staging"]
  lifecycle { destroy = false }
}

removed {
  from = railway_variable.web_sync_public_key["production"]
  lifecycle { destroy = false }
}

removed {
  from = railway_variable.web_sync_public_key["staging"]
  lifecycle { destroy = false }
}

removed {
  from = railway_variable.cron_sync_private_key["production"]
  lifecycle { destroy = false }
}

removed {
  from = railway_variable.cron_sync_private_key["staging"]
  lifecycle { destroy = false }
}

removed {
  from = railway_variable.cron_calendar_url["production"]
  lifecycle { destroy = false }
}

removed {
  from = railway_variable.cron_calendar_url["staging"]
  lifecycle { destroy = false }
}
