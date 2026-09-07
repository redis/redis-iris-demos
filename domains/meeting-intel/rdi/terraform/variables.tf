variable "project_id" {
  description = "GCP project that will own the GKE cluster. Required."
  type        = string
}

variable "region" {
  description = "GCP region for the GKE control plane."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for the node pool (zonal cluster keeps the demo cheaper)."
  type        = string
  default     = "us-central1-a"
}

variable "cluster_name" {
  description = "GKE cluster name."
  type        = string
  default     = "meeting-intel-rdi"
}

variable "network" {
  description = "VPC network name."
  type        = string
  default     = "default"
}

variable "subnetwork" {
  description = "Subnetwork name. Empty uses the default subnet in the region."
  type        = string
  default     = ""
}

variable "machine_type" {
  description = "Node machine type. RDI + Redis Enterprise + Postgres need more than the 4CPU/8GB local-k8s floor."
  type        = string
  default     = "e2-standard-4"
}

variable "node_count" {
  description = "Node count. Three e2-standard-4 nodes (~12 vCPU / 48 GB) is the intended demo size."
  type        = number
  default     = 3
}

variable "disk_size_gb" {
  description = "Boot disk per node."
  type        = number
  default     = 100
}

variable "rdi_chart_version" {
  description = "RDI Helm chart version downloaded from Redis software downloads."
  type        = string
  default     = "1.14.0"
}

variable "redis_host" {
  description = "Target Redis Cloud host from REDIS_HOST / .env. RDI writes synced JSON here."
  type        = string
}

variable "redis_port" {
  description = "Target Redis Cloud port from REDIS_PORT."
  type        = number
}

variable "redis_username" {
  description = "Target Redis username from REDIS_USERNAME."
  type        = string
  default     = "default"
}

variable "redis_password" {
  description = "Target Redis password from REDIS_PASSWORD. Never commit this."
  type        = string
  sensitive   = true
}

variable "redis_ssl" {
  description = "Whether the target Redis Cloud DB expects TLS."
  type        = bool
  default     = false
}

variable "postgres_password" {
  description = "Password for the in-cluster Postgres superuser."
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "dbz_password" {
  description = "Password for the Debezium replication user."
  type        = string
  default     = "dbz"
  sensitive   = true
}
