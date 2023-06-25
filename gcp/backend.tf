terraform {
  backend "gcs" {
    bucket = "jmuleiro-tfstate"
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