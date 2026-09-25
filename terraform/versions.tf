terraform {
  required_version = "~> 1.16.3"

  required_providers {
    railway = {
      source  = "terraform-community-providers/railway"
      version = "~> 0.6"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }

  cloud {
    organization = "cbrcoding-personal"
    workspaces {
      name = "hasl-calendar-prod"
    }
  }
}
