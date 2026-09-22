provider "railway" {
  token = var.railway_token
}

provider "github" {
  token = var.github_token
  owner = var.github_owner
}
