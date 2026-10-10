resource "helm_release" "ingress_nginx" {
  name             = "ingress-nginx"
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  wait             = true
  timeout          = 600

  depends_on = [google_container_node_pool.rdi]
}

resource "kubernetes_namespace" "rdi" {
  metadata {
    name = "rdi"
  }
  depends_on = [google_container_node_pool.rdi]
}

resource "kubernetes_namespace" "meeting_intel" {
  metadata {
    name = "meeting-intel"
  }
  depends_on = [google_container_node_pool.rdi]
}

resource "kubernetes_secret" "target_redis" {
  metadata {
    name      = "meeting-intel-target-redis"
    namespace = kubernetes_namespace.rdi.metadata[0].name
  }
  data = {
    host     = var.redis_host
    port     = tostring(var.redis_port)
    username = var.redis_username
    password = var.redis_password
    ssl      = var.redis_ssl ? "true" : "false"
  }
}

resource "kubernetes_config_map" "postgres_init" {
  metadata {
    name      = "meeting-intel-pg-init"
    namespace = kubernetes_namespace.meeting_intel.metadata[0].name
  }
  data = {
    "00-schema.sql" = file("${path.module}/../source-db/scripts/00-schema.sql")
    "01-seed.sql"   = file("${path.module}/../source-db/scripts/01-seed.sql")
  }
}

resource "kubernetes_secret" "postgres" {
  metadata {
    name      = "meeting-intel-postgres"
    namespace = kubernetes_namespace.meeting_intel.metadata[0].name
  }
  data = {
    POSTGRES_USER     = "postgres"
    POSTGRES_PASSWORD = var.postgres_password
    POSTGRES_DB       = "postgres"
    DBZ_PASSWORD      = var.dbz_password
  }
}

resource "null_resource" "install_rdi" {
  triggers = {
    cluster        = google_container_cluster.rdi.id
    node_pool      = google_container_node_pool.rdi.id
    chart_version  = var.rdi_chart_version
    postgres_cm    = kubernetes_config_map.postgres_init.metadata[0].name
    target_secret  = kubernetes_secret.target_redis.metadata[0].name
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    environment = {
      PROJECT_ID         = var.project_id
      ZONE               = var.zone
      CLUSTER_NAME       = var.cluster_name
      RDI_CHART_VERSION  = var.rdi_chart_version
      KUBECONFIG_PATH    = "${path.module}/generated/kubeconfig"
    }
    command = "${path.module}/scripts/install-rdi.sh"
  }

  depends_on = [
    helm_release.ingress_nginx,
    kubernetes_namespace.rdi,
    kubernetes_namespace.meeting_intel,
    kubernetes_secret.target_redis,
    kubernetes_secret.postgres,
    kubernetes_config_map.postgres_init,
  ]
}
