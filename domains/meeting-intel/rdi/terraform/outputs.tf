output "cluster_name" {
  value = google_container_cluster.rdi.name
}

output "cluster_endpoint" {
  value     = google_container_cluster.rdi.endpoint
  sensitive = true
}

output "get_credentials_command" {
  value = "gcloud container clusters get-credentials ${google_container_cluster.rdi.name} --zone ${var.zone} --project ${var.project_id}"
}

output "rdi_namespace" {
  value = "rdi"
}

output "postgres_service" {
  value = "postgres.meeting-intel.svc.cluster.local:5432"
}

output "target_redis_secret" {
  value = "meeting-intel-target-redis (rdi namespace)"
}

output "next_steps" {
  value = <<-EOT
    1. gcloud container clusters get-credentials ${var.cluster_name} --zone ${var.zone} --project ${var.project_id}
    2. kubectl get pod -n rdi
    3. kubectl get pod -n meeting-intel
    4. export RDI_API_URL=http://<rdi-api-ingress>
    5. make mi-rdi-pipeline
    6. make mi-verify
  EOT
}
