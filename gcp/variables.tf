#* --- Google Cloud Platform
variable "project" {
  type = string
  description = "Google Cloud Platform project"
}

variable "region" {
  type = string
  description = "Default Google Cloud Compute Engine region"
  default = ""
}

variable "zone" {
  type = string
  description = "Default Google Cloud Compute Engine zone"
  default = ""
}

#* --- Metadata
variable "tags" {
  type = list(string)
  description = "List of tags to use for all resources, whenever possible"
  default = ["terraform"]
}

variable "labels" {
  type = map(string)
  description = "Map of labels to use for all resources, whenever possible"
  default = {
    "maintained_by" = "terraform"
  }
}

#* --- Cloud DNS
variable "jmuleiro_domain" {
  type = string
  description = "Jmuleiro domain name"
  default = "jmuleiro.com."
#  validation {
#    condition = can(regex("^(?!-)[A-Za-z0-9-]{1,63}(?<!-)\\.(?:[A-Za-z]{2}(?:\\.[A-Za-z]{2})?)$", var.jmuleiro_domain))
#    error_message = "Invalid domain name"
#  }
}

variable "alcanza_domain" {
  type = string
  description = "Alcanza Poesia domain name"
  default = "lapoesiaalcanza.com.ar."
#  validation {
#    condition = can(regex("^(?!-)[A-Za-z0-9-]{1,63}(?<!-)\\.(?:[A-Za-z]{2}(?:\\.[A-Za-z]{2})?)$", var.alcanza_domain))
#    error_message = "Invalid domain name"
#  }
}

variable "alcanza_ip" {
  type = string
  description = "Alcanza Poesia public IPv4 address"
  validation {
    condition = can(regex("^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$", var.alcanza_ip))
    error_message = "Invalid IPv4 address format"
  }
}

#* --- Google Kubernetes Engine Cluster
variable "cluster_version" {
  type = string
  description = "Google Kubernetes Engine cluster master version"
  default = "1.26.5-gke.1200"
}
variable "cluster_ip_whitelist" {
  type = list(string)
  description = "List of IP addresses to whitelist for IAP access to the Kubernetes API"
  default = [ "" ]
}