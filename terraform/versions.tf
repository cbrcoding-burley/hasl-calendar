terraform {
  required_version = ">= 1.6"

  required_providers {
    railway = {
      source  = "railwayapp/railway"
      version = "~> 0.4"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }

  # ── State backend ────────────────────────────────────────────────────────────
  # Default: local state, one file per workspace under terraform.tfstate.d/.
  # These files contain sensitive values (Railway tokens, private keys) —
  # keep them off shared drives and out of git.
  #
  # Better free alternative — HCP Terraform (formerly Terraform Cloud):
  #   1. Sign up at app.terraform.io, create an org
  #   2. Run: terraform login
  #   3. Replace this block with:
  #        backend "remote" {
  #          organization = "<your-hcp-org>"
  #          workspaces { prefix = "hasl-calendar-" }
  #        }
  #   4. terraform init -migrate-state
  #   This gives you encrypted remote state, run history, and drift detection
  #   with zero infra to manage. Free up to 500 resources.
  #
  # Other free options:
  #   • Cloudflare R2 (S3-compatible, 10 GB free):
  #       backend "s3" { endpoint = "..." bucket = "tf-state" ... }
  #   • GitLab-managed Terraform state (if you ever move the repo there)

  backend "local" {}
}
