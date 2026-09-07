terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.40"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.40"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.14"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.31"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.2"
    }
  }
}
