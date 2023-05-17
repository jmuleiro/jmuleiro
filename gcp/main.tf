#* --- Providers
provider "google" {
  project = var.project
  region = var.region
  zone = var.zone
}

#* --- Locals
locals {
  services_range_name = "cluster-services-range"
  pods_range_name = "cluster-pods-range"
}

#* --- APIs
#TODO: add api resources

#* --- Cloud DNS
#** jmuleiro.com
resource "google_dns_managed_zone" "jmuleiro" {
  name = "jmuleiro-com"
  dns_name = var.jmuleiro_domain
  description = "Main domain DNS zone"
  labels = var.labels
}

resource "google_dns_record_set" "jmuleiro-mx" {
  name = google_dns_managed_zone.jmuleiro.dns_name
  managed_zone = google_dns_managed_zone.jmuleiro.name
  type = "MX"
  ttl = 3600

  rrdatas = [
    "1 aspmx.l.google.com.",
    "5 alt1.aspmx.l.google.com.",
    "5 alt2.aspmx.l.google.com.",
    "10 alt3.aspmx.l.google.com.",
    "10 alt4.aspmx.l.google.com."
  ]
}

resource "google_dns_record_set" "jmuleiro-spf" {
  name = "_spf.${google_dns_managed_zone.jmuleiro.dns_name}"
  managed_zone = google_dns_managed_zone.jmuleiro.name
  type = "TXT"
  ttl = 3600

  rrdatas = [
    "v=spf1 include:_spf.google.com ~all"
  ]
}

resource "google_dns_record_set" "jmuleiro-txt" {
  name = google_dns_managed_zone.jmuleiro.dns_name
  managed_zone = google_dns_managed_zone.jmuleiro.name
  type = "TXT"
  ttl = 300

  rrdatas = [
    "v=spf1 include:_spf.${google_dns_managed_zone.jmuleiro.dns_name} ~all",
    "google-site-verification=UQwonYrFpWnz6H5CMUrTznPShb4zNKSJSaza083DpBU"
  ]
}
#TODO: add gmail domain key & enable dmarc
resource "google_dns_record_set" "jmuleiro-dmarc" {
  name = "_dmarc.${google_dns_managed_zone.jmuleiro.dns_name}"
  managed_zone = google_dns_managed_zone.jmuleiro.name
  type = "TXT"
  ttl = 300

  rrdatas = [
    "v=DMARC1; p=none; aspf=s; adkim=s;"
  ]
}

#** lapoesiaalcanza.com.ar
resource "google_dns_managed_zone" "alcanza" {
  name = "alcanza-poesia"
  dns_name = var.alcanza_domain
  description = "Main domain zone for La Poesia Alcanza para Todos"
  labels = var.labels
}

resource "google_dns_record_set" "alcanza-a" {
  name = google_dns_managed_zone.alcanza.dns_name
  managed_zone = google_dns_managed_zone.alcanza.name
  type = "A"
  ttl = 300

  rrdatas = [var.alcanza_ip]
}

resource "google_dns_record_set" "alcanza-txt" {
  name = google_dns_managed_zone.alcanza.dns_name
  managed_zone = google_dns_managed_zone.alcanza.name
  type = "TXT"
  ttl = 300

  rrdatas = [
    "v=spf1 -all",
    "google-site-verification=MZTawTWDWHda0n-kXRxa31_Tc-Y2ixN5OHRNvrBuILY"
  ]
}

resource "google_dns_record_set" "alcanza-mx" {
  name = google_dns_managed_zone.alcanza.dns_name
  managed_zone = google_dns_managed_zone.alcanza.name
  type = "MX"
  ttl = 3600

  rrdatas = [
    "0 ."
  ]
}

resource "google_dns_record_set" "alcanza-cname-www" {
  name = "www.${google_dns_managed_zone.alcanza.dns_name}"
  managed_zone = google_dns_managed_zone.alcanza.name
  type = "CNAME"
  ttl = 300

  rrdatas = [
    "${var.alcanza_domain}."
  ]
}

#* --- Cloud VPC
resource "google_compute_network" "gke-network" {
  name = "gke-network"
  description = "Main VPC network used for the Kubernetes cluster"
  auto_create_subnetworks = false
  delete_default_routes_on_create = true
  routing_mode = "GLOBAL"
}

resource "google_compute_subnetwork" "gke-subnet" {
  name = "gke-subnet"
  ip_cidr_range = "10.255.0.0/16"
  network = google_compute_network.gke-network.id
  
  secondary_ip_range {
    range_name = local.pods_range_name
    ip_cidr_range = "10.0.0.0/16"
  }

  secondary_ip_range {
    range_name = local.services_range_name
    ip_cidr_range = "10.64.0.0/16"
  }
}

#* --- IAM
resource "google_service_account" "gke-cluster" {
  account_id = "gke"
  display_name = "GKE Service Account"
  description = "Google Kubernetes Engine Service Account"
}

resource "google_project_iam_custom_role" "gke-cluster" {
  role_id = "jmuleiro.gke"
  title = "Google Kubernetes Engine Cluster"
  description = "Custom role for GKE clusters. Should not be attached to non-system service accounts"
  permissions = [
    #TODO: lookup permissions
  ]
}

#* --- GKE
resource "google_container_cluster" "main-cluster" {
  #? Metadata
  name = "jmuleiro-prod"
  description = "GKE cluster used for hosting multiple projects"

  #? Cluster configurations
  initial_node_count = 1
  remove_default_node_pool = true
  location = var.zone
  min_master_version = "1.24.11-gke.1000"
  release_channel {
    channel = "STABLE"
  }

  #? Network configurations
  networking_mode = "VPC_NATIVE"
  network = google_compute_network.gke-network.self_link
  subnetwork = google_compute_subnetwork.gke-subnet.self_link
  ip_allocation_policy {
    cluster_secondary_range_name = local.pods_range_name
    services_secondary_range_name = local.services_range_name
  }

  #? Addons & Features
  addons_config {
    horizontal_pod_autoscaling {
      disabled = true
    }
    http_load_balancing {
      disabled = true
    }
    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
  }
  logging_config {
    enable_components = []
  }
  logging_service = "none"
  monitoring_config {
    enable_components = []
  }
  monitoring_service = "none"
}