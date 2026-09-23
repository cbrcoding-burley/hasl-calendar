terraform {
  required_version = ">= 1.7"

  required_providers {
    railway = {
      source  = "terraform-community-providers/railway"
      version = "~> 0.4"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
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
  #
  # Other free option: Cloudflare R2 (S3-compatible, 10 GB free, no egress fees)

  backend "local" {}
}
