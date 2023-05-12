#* --- Providers
provider "google" {
  project = var.project
  region = var.region
  zone = var.zone
}

#* --- Cloud DNS
#** jmuleiro.com
resource "google_dns_managed_zone" "jmuleiro" {
  name = "jmuleiro-com"
  dns_name = var.jmuleiro_domain
  description = "Main domain DNS zone"
  labels = {
    "project" = "jmuleiro"
    "created_by" = "terraform"
  }
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
  labels = {
    "project" = "alcanza-poesia"
    "created_by" = "terraform"
  }
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
resource "google_compute_network" "prod-network" {
  name = "prod-network"
  description = "Main VPC network used for the Kubernetes cluster"
  auto_create_subnetworks = false
  delete_default_routes_on_create = true
}
