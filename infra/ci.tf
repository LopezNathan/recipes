# Keyless auth for GitHub Actions via Workload Identity Federation:
# workflows exchange their GitHub OIDC token for short-lived credentials of a
# dedicated, narrowly-scoped CI service account — no exported key anywhere.

locals {
  github_repo = "LopezNathan/recipes"
}

resource "google_project_service" "ci" {
  for_each = toset([
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

resource "google_service_account" "github_ci" {
  account_id   = "github-ci"
  display_name = "GitHub Actions CI"
  depends_on   = [google_project_service.ci]
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.ci]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == \"${local.github_repo}\""
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Only workflows from this repo may impersonate the CI service account.
resource "google_service_account_iam_member" "wif_impersonation" {
  service_account_id = google_service_account.github_ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${local.github_repo}"
}

resource "google_project_iam_member" "ci_compute" {
  project = var.project_id
  role    = "roles/compute.admin"
  member  = "serviceAccount:${google_service_account.github_ci.email}"
}

# The instance runs as the default compute service account; creating it
# (weekly -replace) requires actAs on that account. Scoped to the one SA
# rather than a project-wide serviceAccountUser grant.
data "google_compute_default_service_account" "default" {}

resource "google_service_account_iam_member" "ci_actas_default_compute" {
  service_account_id = data.google_compute_default_service_account.default.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_ci.email}"
}

# State access, scoped to the tfstate bucket only. legacyBucketReader supplies
# storage.buckets.get, which the gcs backend needs alongside object CRUD.
resource "google_storage_bucket_iam_member" "ci_state_objects" {
  bucket = "recipes-496402-tfstate"
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_ci.email}"
}

resource "google_storage_bucket_iam_member" "ci_state_bucket" {
  bucket = "recipes-496402-tfstate"
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:${google_service_account.github_ci.email}"
}

output "wif_provider" {
  description = "Value for google-github-actions/auth workload_identity_provider"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "ci_service_account" {
  description = "Value for google-github-actions/auth service_account"
  value       = google_service_account.github_ci.email
}
