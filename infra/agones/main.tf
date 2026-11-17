terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
    helm = { source = "hashicorp/helm", version = "~> 2.13" }
  }
  backend "gcs" {}
}
variable "project" { type = string }
variable "cluster" { default = "bloques-dev" }
variable "zone" { default = "us-central1-a" }
provider "google" { project = var.project }
data "google_client_config" "current" {}
data "google_container_cluster" "game" {
  name = var.cluster
  location = var.zone
}
provider "helm" {
  kubernetes {
    host = "https://${data.google_container_cluster.game.endpoint}"
    token = data.google_client_config.current.access_token
    cluster_ca_certificate = base64decode(data.google_container_cluster.game.master_auth[0].cluster_ca_certificate)
  }
}
resource "helm_release" "agones" {
  name = "agones"
  repository = "https://agones.dev/chart/stable"
  chart = "agones"
  version = "1.62.0"
  namespace = "agones-system"
  create_namespace = true
  timeout = 600
  set {
    name = "gameservers.minPort"
    value = "7000"
  }
  set {
    name = "gameservers.maxPort"
    value = "8000"
  }
}
