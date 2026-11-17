terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
  backend "gcs" {}
}
provider "google" {
  project = var.project
  region  = var.region
  zone    = var.zone
}
variable "project" { type = string }
variable "region" { default = "us-central1" }
variable "zone" { default = "us-central1-a" }
variable "environment" { default = "dev" }
variable "max_nodes" { default = 20 }
variable "client_cidrs" {
  type        = list(string)
  description = "CIDR públicos de los jugadores/generadores del laboratorio"
}
variable "admin_cidrs" {
  type        = list(string)
  description = "CIDR /32 del administrador y del runner de despliegue"
}
variable "leaderboard_image" {
  type        = string
  description = "Imagen publicada de serverless, con etiqueta SHA"
}
locals { prefix = "bloques-${var.environment}" }
resource "google_project_service" "api" {
  for_each = toset(["compute.googleapis.com", "container.googleapis.com", "artifactregistry.googleapis.com", "run.googleapis.com", "firestore.googleapis.com", "iam.googleapis.com"])
  service = each.key
  disable_on_destroy = false
}
resource "google_compute_network" "vpc" {
  name = "${local.prefix}-vpc"
  auto_create_subnetworks = false
  depends_on = [google_project_service.api]
}
resource "google_compute_subnetwork" "subnet" {
  name = "${local.prefix}-subnet"
  region = var.region
  network = google_compute_network.vpc.id
  ip_cidr_range = "10.20.0.0/20"
  secondary_ip_range {
    range_name = "pods"
    ip_cidr_range = "10.24.0.0/14"
  }
  secondary_ip_range {
    range_name = "services"
    ip_cidr_range = "10.28.0.0/20"
  }
}
resource "google_compute_firewall" "games" {
  name = "${local.prefix}-games"
  network = google_compute_network.vpc.id
  source_ranges = var.client_cidrs
  target_tags = ["bloques-games"]
  allow {
    protocol = "tcp"
    ports = ["7000-8000"]
  }
}
resource "google_service_account" "nodes" {
  account_id = "${local.prefix}-nodes"
  depends_on = [google_project_service.api]
}
resource "google_project_iam_member" "nodes" {
  for_each = toset(["roles/logging.logWriter", "roles/monitoring.metricWriter", "roles/artifactregistry.reader"])
  project = var.project
  role = each.key
  member = "serviceAccount:${google_service_account.nodes.email}"
}
resource "google_container_cluster" "game" {
  name = local.prefix
  location = var.zone
  network = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.subnet.id
  initial_node_count = 1
  remove_default_node_pool = true
  deletion_protection = false
  release_channel { channel = "REGULAR" }
  workload_identity_config { workload_pool = "${var.project}.svc.id.goog" }
  ip_allocation_policy {
    cluster_secondary_range_name = "pods"
    services_secondary_range_name = "services"
  }
  master_authorized_networks_config {
    dynamic "cidr_blocks" {
      for_each = var.admin_cidrs
      content {
        cidr_block = cidr_blocks.value
        display_name = "admin-${cidr_blocks.key}"
      }
    }
  }
}
resource "google_container_node_pool" "games" {
  name = "games"
  location = var.zone
  cluster = google_container_cluster.game.id
  initial_node_count = 3
  autoscaling {
    min_node_count = 3
    max_node_count = var.max_nodes
  }
  management {
    auto_repair = true
    auto_upgrade = true
  }
  node_config {
    machine_type = "e2-standard-4"
    disk_size_gb = 30
    service_account = google_service_account.nodes.email
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    tags = ["bloques-games"]
    labels = { component = "game", environment = var.environment }
    workload_metadata_config { mode = "GKE_METADATA" }
  }
  depends_on = [google_project_iam_member.nodes]
}
resource "google_artifact_registry_repository" "images" {
  location = var.region
  repository_id = "bloques"
  format = "DOCKER"
  depends_on = [google_project_service.api]
}
resource "google_service_account" "leaderboard" {
  account_id = "${local.prefix}-scores"
  depends_on = [google_project_service.api]
}
resource "google_project_iam_member" "scores" {
  project = var.project
  role = "roles/datastore.user"
  member = "serviceAccount:${google_service_account.leaderboard.email}"
}
resource "google_firestore_database" "scores" {
  project = var.project
  name = "(default)"
  location_id = var.region
  type = "FIRESTORE_NATIVE"
  delete_protection_state = "DELETE_PROTECTION_DISABLED"
  deletion_policy = "DELETE"
  depends_on = [google_project_service.api]
}
resource "google_cloud_run_v2_service" "scores" {
  name = "${local.prefix}-scores"
  location = var.region
  deletion_protection = false
  template {
    service_account = google_service_account.leaderboard.email
    max_instance_request_concurrency = 40
    scaling {
      min_instance_count = 0
      max_instance_count = 50
    }
    containers {
      image = var.leaderboard_image
      env {
        name = "STORAGE"
        value = "firestore"
      }
      resources {
        limits = { cpu = "1", memory = "256Mi" }
        cpu_idle = true
      }
    }
  }
  depends_on = [google_project_iam_member.scores, google_firestore_database.scores]
}
output "cluster" { value = google_container_cluster.game.name }
output "registry" { value = "${var.region}-docker.pkg.dev/${var.project}/bloques" }
output "leaderboard_url" { value = google_cloud_run_v2_service.scores.uri }
resource "google_service_account" "game" {
  account_id = "${local.prefix}-game"
  depends_on = [google_project_service.api]
}
resource "google_service_account_iam_member" "game_identity" {
  service_account_id = google_service_account.game.name
  role = "roles/iam.workloadIdentityUser"
  member = "serviceAccount:${var.project}.svc.id.goog[default/bloques-game]"
}
resource "google_cloud_run_v2_service_iam_member" "game_invoker" {
  project = var.project
  location = var.region
  name = google_cloud_run_v2_service.scores.name
  role = "roles/run.invoker"
  member = "serviceAccount:${google_service_account.game.email}"
}
