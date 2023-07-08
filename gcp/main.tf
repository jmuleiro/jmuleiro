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
resource "google_project_service" "storage" {
  project = var.project
  service = "storage.googleapis.com"
  disable_dependent_services = false
}

resource "google_project_service" "iam" {
  project = var.project
  service = "iam.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy = false
}

resource "google_project_service" "gce" {
  project = var.project
  service = "compute.googleapis.com"
  disable_dependent_services = false
}

resource "google_project_service" "gke" {
  project = var.project
  service = "container.googleapis.com"
  disable_dependent_services = false
}

resource "google_project_service" "dns" {
  project = var.project
  service = "dns.googleapis.com"
  disable_dependent_services = false
}

resource "google_project_service" "artifact_registry" {
  project = var.project
  service = "artifactregistry.googleapis.com"
  disable_dependent_services = false
}

#* --- Cloud DNS
#** jmuleiro.com
resource "google_dns_managed_zone" "jmuleiro" {
  depends_on = [ google_project_service.dns ]
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
    "\"v=spf1 include:_spf.google.com ~all\""
  ]
}

resource "google_dns_record_set" "jmuleiro-txt" {
  name = google_dns_managed_zone.jmuleiro.dns_name
  managed_zone = google_dns_managed_zone.jmuleiro.name
  type = "TXT"
  ttl = 300

  rrdatas = [
    "\"v=spf1 include:_spf.${google_dns_managed_zone.jmuleiro.dns_name} ~all\"",
    "\"google-site-verification=UQwonYrFpWnz6H5CMUrTznPShb4zNKSJSaza083DpBU\""
  ]
}

resource "google_dns_record_set" "jmuleiro-dkim" {
  name = "google._domainkey.${google_dns_managed_zone.jmuleiro.dns_name}"
  managed_zone = google_dns_managed_zone.jmuleiro.name
  type = "TXT"
  ttl = 300

  rrdatas = [
    "\"v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAiKcqRnfdurVWunVbN80MrUBheZO+GcFJQIhbeMRh/O2zUNvUCW7HL6EoKNSVuzYf+qLa35dIW6Q1zBj4IfyGSOVz+\" \"krx9uFoAYeSaO59rBXCgjt68suzmHpRXtKiFX5anaLV8ROLxOmCxY4NgzL7JbfybtOXgm6fHL9twCTBjxNIaRb4NxQcsqAzp5xRTUwaWdfQ3Yt9ml8cIp5gGT8x5VGFAeOWks8P5IzgQ8L+wxD/znwkh1qqUW4FR9LSBOEzLo/WGYRa9U33bVx4xuhuuu67+kWw03Qt39/\" \"4eZZg2YSiWwTRQ1o3C5Unuh6Tj9iLlMzJP5sp7ECXSeA8Ob9DnwIDAQAB\""
  ]
}

resource "google_dns_record_set" "jmuleiro-dmarc" {
  name = "_dmarc.${google_dns_managed_zone.jmuleiro.dns_name}"
  managed_zone = google_dns_managed_zone.jmuleiro.name
  type = "TXT"
  ttl = 300

  rrdatas = [
    "\"v=DMARC1; p=none; aspf=s; adkim=s;\""
  ]
}

#** lapoesiaalcanza.com.ar
resource "google_dns_managed_zone" "alcanza" {
  depends_on = [ google_project_service.dns ]
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
    "\"v=spf1 -all\"",
    "\"google-site-verification=MZTawTWDWHda0n-kXRxa31_Tc-Y2ixN5OHRNvrBuILY\""
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
    "${var.alcanza_domain}"
  ]
}

#* --- Cloud VPC
resource "google_compute_network" "gke-network" {
  depends_on = [ google_project_service.gce ]
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
  depends_on = [ google_project_service.iam ]
  account_id = "google-kubernetes-engine"
  display_name = "GKE Service Account"
  description = "Google Kubernetes Engine Service Account"
}

resource "google_project_iam_custom_role" "gke-cluster" {
  depends_on = [ google_project_service.iam ]
  role_id = "jmuleiro.gke"
  title = "Google Kubernetes Engine Cluster"
  description = "Custom role for GKE clusters. Should not be attached to non-system service accounts"
  permissions = [
    "monitoring.timeSeries.list",
    "monitoring.metricDescriptors.create",
    "artifactregistry.repositories.downloadArtifacts",
    "autoscaling.sites.writeMetrics",
    "logging.logEntries.create",
    "monitoring.metricDescriptors.list",
    "monitoring.timeSeries.create",
    "storage.objects.get",
    "storage.objects.list",
    "appengine.applications.get",
    "appengine.instances.get",
    "appengine.instances.list",
    "appengine.operations.get",
    "appengine.operations.list",
    "appengine.services.get",
    "appengine.services.list",
    "appengine.versions.create",
    "appengine.versions.get",
    "appengine.versions.list",
    "resourcemanager.projects.get",
    "serviceusage.services.use"
  ]
}

resource "google_project_iam_member" "gke-cluster" {
  project = var.project
  role = "projects/${var.project}/roles/${google_project_iam_custom_role.gke-cluster.role_id}"
  member = "serviceAccount:${google_service_account.gke-cluster.email}"
}
#* --- Artifact Registry
resource "google_artifact_registry_repository" "alcanza_docker" {
  depends_on = [ google_project_service.artifact_registry ]
  repository_id = "alcanza-poesia"
  format = "DOCKER"
  location = var.region
  description = "Alcanza Poesia"
  labels = merge(var.labels, {"project": "alcanza"})
}

#* --- GKE
resource "google_container_cluster" "main-cluster" {
  depends_on = [ google_project_service.gce, google_project_service.iam, google_project_service.gke ]
  #? Metadata
  name = "jmuleiro-prod"
  description = "GKE cluster used for hosting multiple projects"

  #? Cluster configurations
  initial_node_count = 1
  remove_default_node_pool = true
  location = var.zone
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
  #logging_service = "none"
  monitoring_config {
    enable_components = []
  }
  #monitoring_service = "none"
}

resource "google_container_node_pool" "prod-main-0" {
  cluster = google_container_cluster.main-cluster.name
  location = var.zone
  name = "prod-main-0"
  node_count = 1
  version = google_container_cluster.main-cluster.master_version

  node_locations = [
    var.zone
  ]
  management {
    auto_repair = true
    auto_upgrade = true
  }
  network_config {
    enable_private_nodes = true
  }
  upgrade_settings {
    max_surge = 1
    max_unavailable = 0
  }
  node_config {
    disk_size_gb = 20
    disk_type = "pd-balanced"
    image_type = "cos_containerd"
    local_ssd_count = 0
    machine_type = "e2-highcpu-2"
    spot = false
    preemptible = false
    service_account = google_service_account.gke-cluster.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}

resource "google_container_node_pool" "prod-main-1" {
  cluster = google_container_cluster.main-cluster.name
  location = var.zone
  name = "prod-main-1"
  node_count = 1
  version = google_container_cluster.main-cluster.master_version
  
  node_locations = [
    var.zone
  ]
  management {
    auto_repair = true
    auto_upgrade = true
  }
  network_config {
    enable_private_nodes = true
  }
  upgrade_settings {
    max_surge = 1
    max_unavailable = 0
  }
  node_config {
    disk_size_gb = 20
    disk_type = "pd-balanced"
    image_type = "cos_containerd"
    local_ssd_count = 0
    machine_type = "n1-standard-1"
    spot = false
    preemptible = false
    service_account = google_service_account.gke-cluster.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}