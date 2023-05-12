terraform {
  backend "gcs" {
    bucket = "jmuleiro-tfstate-prod"
    prefix = "state/jmuleiro"
  }
  
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "4.64.0"
    }
  }

  required_version = ">= 1.4.6"
}