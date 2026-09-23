terraform {
  required_providers {
    railway = {
      source = "terraform-community-providers/railway"
    }
    github = {
      source = "integrations/github"
    }
    cloudflare = {
      source = "cloudflare/cloudflare"
    }
  }
}
