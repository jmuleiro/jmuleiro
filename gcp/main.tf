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
  #Usable Host IP Range:	10.10.7.1 - 10.10.7.14
  master_range_cidr = "10.10.7.0/28"
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
  # Usable Host IP Range:	10.10.0.1 - 10.10.63.254
  ip_cidr_range = "10.10.0.0/18" 
  network = google_compute_network.gke-network.id
  
  secondary_ip_range {
    range_name = local.pods_range_name
    # Usable Host IP Range:	10.10.8.1 - 10.10.15.254
    ip_cidr_range = "10.10.10.0/21"
  }

  secondary_ip_range {
    range_name = local.services_range_name
    # Usable Host IP Range:	10.10.16.1 - 10.10.23.254
    ip_cidr_range = "10.10.20.0/21"
  }
}
#TODO: review if this is necessary or it could be done some other way
# with Cloud IAP
resource "google_compute_address" "gke-master" {
  name = "gke-master-internal"
  address_type = "INTERNAL"
  subnetwork = google_compute_subnetwork.gke-subnet.name
  description = "Internal IP address for GKE master access through IAP"
  address = "10.10.0.10"
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
  name = "jmuleiro-prod-3"
  description = "GKE cluster used for hosting multiple projects"

  #? Cluster configurations
  remove_default_node_pool = true
  initial_node_count = 1
  location = var.zone
  min_master_version = var.cluster_version
  release_channel {
    channel = "STABLE"
  }

  #? Network configurations
  networking_mode = "VPC_NATIVE"
  network = google_compute_network.gke-network.self_link
  subnetwork = google_compute_subnetwork.gke-subnet.self_link
  private_cluster_config {
    enable_private_endpoint = true
    enable_private_nodes = true
    master_ipv4_cidr_block = local.master_range_cidr
  }
  ip_allocation_policy {
    cluster_secondary_range_name = local.pods_range_name
    services_secondary_range_name = local.services_range_name
  }
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block = "${google_compute_address.gke-master.address}/32"
      display_name = "iap-proxy"
    }
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
  monitoring_config {
    enable_components = []
  }
  vertical_pod_autoscaling {
    enabled = false
  }
  enable_intranode_visibility = false
  timeouts {
    create = "12m"
  }
}

resource "google_container_node_pool" "prod-main-0" {
  cluster = google_container_cluster.main-cluster.name
  location = var.zone
  name = "prod-main-0"
  node_count = 1
  version = google_container_cluster.main-cluster.master_version

#  node_locations = [
#    var.zone
#  ]
  management {
    auto_repair = true
    auto_upgrade = false
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
    labels = merge(var.labels, {"kind": "gke"})
    metadata = {
      disable-legacy-endpoints = "true"
    }
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring"
    ]
  }
}

resource "google_container_node_pool" "prod-main-1" {
  cluster = google_container_cluster.main-cluster.name
  location = var.zone
  name = "prod-main-1"
  node_count = 1
  version = google_container_cluster.main-cluster.master_version
  
#  node_locations = [
#    var.zone
#  ]
  management {
    auto_repair = true
    auto_upgrade = false
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
    labels = merge(var.labels, {"kind": "gke"})
    metadata = {
      disable-legacy-endpoints = "true"
    }
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring"
    ]
  }
}

#* --- Google Compute Firewall & IAP requirements
resource "google_compute_firewall" "gke" {
  name = "allow-ssh"
  network = google_compute_network.gke-network.name
  allow {
    protocol = "tcp"
    ports = ["22"]
  }
  source_ranges = var.cluster_ip_whitelist
}
resource "google_compute_router" "gke" {
  name = "gke-nat"
  network = google_compute_network.gke-network.id
  bgp {
    asn = 64514
  }
}
resource "google_compute_router_nat" "gke" {
  name = "gke-nat"
  router = google_compute_router.gke.name
  nat_ip_allocate_option = "MANUAL_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  log_config {
    enable = false
    filter = "ERRORS_ONLY"
  }
}