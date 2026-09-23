provider "railway" {
  token = var.railway_token
}

provider "github" {
  token = var.github_token
  owner = var.github_owner
}

provider "cloudflare" {
  # Reads CLOUDFLARE_API_TOKEN from environment automatically.
  # Only active when var.cloudflare_zone_id is set.
}
