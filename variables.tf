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

#* --- Cloud DNS
variable "jmuleiro_domain" {
  type = string
  description = "Jmuleiro domain name"
  default = "jmuleiro.com"
  validation {
    condition = can(regex("^(?!-)[A-Za-z0-9-]{1,63}(?<!-)\\.(?:[A-Za-z]{2}(?:\\.[A-Za-z]{2})?)$", var.jmuleiro_domain))
    error_message = "Invalid domain name"
  }
}

variable "alcanza_domain" {
  type = string
  description = "Alcanza Poesia domain name"
  default = "lapoesiaalcanza.com.ar"
  validation {
    condition = can(regex("^(?!-)[A-Za-z0-9-]{1,63}(?<!-)\\.(?:[A-Za-z]{2}(?:\\.[A-Za-z]{2})?)$", var.alcanza_domain))
    error_message = "Invalid domain name"
  }
}

variable "alcanza_ip" {
  type = string
  description = "Alcanza Poesia public IPv4 address"
  validation {
    condition = can(regex("^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$", var.alcanza_ip))
    error_message = "Invalid IPv4 address format"
  }
}