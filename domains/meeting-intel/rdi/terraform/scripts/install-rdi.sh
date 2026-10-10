#!/usr/bin/env bash
# Install Redis Enterprise (RDI backend DB) + RDI Helm + in-cluster Postgres.
# Invoked by terraform null_resource.install_rdi after GKE is up.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${CLUSTER_NAME:?}"
ZONE="${ZONE:?}"
PROJECT_ID="${PROJECT_ID:?}"
RDI_CHART_VERSION="${RDI_CHART_VERSION:-1.14.0}"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-$ROOT/generated/kubeconfig}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is not installed or not on PATH."
  echo "Stop here: this Cloud Agent cannot apply GKE Terraform without GCP credentials."
  exit 2
fi
if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required to install RDI onto GKE."
  exit 2
fi
if ! command -v helm >/dev/null 2>&1; then
  echo "helm is required to install the RDI chart."
  exit 2
fi

mkdir -p "$(dirname "$KUBECONFIG_PATH")"
export KUBECONFIG="$KUBECONFIG_PATH"
gcloud container clusters get-credentials "$CLUSTER_NAME" --zone "$ZONE" --project "$PROJECT_ID"

echo "Installing Redis Enterprise operator into namespace rdi..."
RE_LATEST_VERSION="$(curl --silent https://api.github.com/repos/RedisLabs/redis-enterprise-k8s-docs/releases/latest | grep tag_name | awk -F'"' '{print $4}')"
kubectl apply -f "https://raw.githubusercontent.com/RedisLabs/redis-enterprise-k8s-docs/${RE_LATEST_VERSION}/bundle.yaml" -n rdi

echo "Waiting for Redis Enterprise operator..."
for _ in $(seq 1 60); do
  STATUS="$(kubectl get deployment redis-enterprise-operator -n rdi -o jsonpath='{.status.readyReplicas}' 2>/dev/null || true)"
  if [[ "$STATUS" == "1" ]]; then
    break
  fi
  sleep 5
done
if [[ "$STATUS" != "1" ]]; then
  echo "Redis Enterprise operator did not become ready."
  exit 1
fi

kubectl apply -f "$ROOT/k8s/rdi-rec.yaml"
echo "Waiting for Redis Enterprise Cluster pod..."
kubectl wait --for=condition=Ready pod/redis-enterprise-cluster-0 -n rdi --timeout=600s || true

kubectl apply -f "$ROOT/k8s/rdi-db.yaml"
echo "Waiting for RDI backend database..."
for _ in $(seq 1 60); do
  DBSTATUS="$(kubectl get redb rdidb -n rdi -o jsonpath='{.status.status}' 2>/dev/null || true)"
  if [[ "$DBSTATUS" == "active" ]]; then
    break
  fi
  sleep 5
done
if [[ "$DBSTATUS" != "active" ]]; then
  echo "RDI database did not become active."
  exit 1
fi

CHART="rdi-${RDI_CHART_VERSION}.tgz"
CHART_PATH="$ROOT/generated/$CHART"
mkdir -p "$ROOT/generated"
if [[ ! -f "$CHART_PATH" ]]; then
  curl -L "https://redis-enterprise-software-downloads.s3.amazonaws.com/redis-di/${CHART}" -o "$CHART_PATH"
fi

RDI_DATABASE_HOST="rdidb.rdi.svc.cluster.local"
RDI_DATABASE_PORT="$(kubectl get secret redb-rdidb -o jsonpath='{.data.port}' -n rdi | base64 --decode)"
RDI_DATABASE_PASSWORD="$(kubectl get secret redb-rdidb -o jsonpath='{.data.password}' -n rdi | base64 --decode)"
JWT_KEY="$(head -c 32 /dev/urandom | base64)"

cat > "$ROOT/generated/rdi-values.yaml" <<EOF
connection:
  host: "$RDI_DATABASE_HOST"
  port: "$RDI_DATABASE_PORT"
  password: "$RDI_DATABASE_PASSWORD"

api:
  jwtKey: "$JWT_KEY"

ingress:
  enabled: true
  className: "nginx"
EOF

helm upgrade --install rdi "$CHART_PATH" -f "$ROOT/generated/rdi-values.yaml" -n rdi --wait --timeout 10m

kubectl apply -f "$ROOT/k8s/postgres.yaml"
echo "Waiting for in-cluster Postgres..."
kubectl rollout status statefulset/postgres -n meeting-intel --timeout=300s || true

echo "RDI API ingress (set RDI_API_URL to this):"
kubectl get ingress -n rdi -o wide || true
echo "JWT for RDI API is in $ROOT/generated/rdi-values.yaml under api.jwtKey (do not commit)."
echo "export RDI_API_TOKEN=<api.jwtKey from rdi-values.yaml>"
echo "Source DB for the pipeline: postgres.meeting-intel.svc.cluster.local:5432"
echo "Target Redis: secret meeting-intel-target-redis in namespace rdi (from REDIS_* / .env)."
echo "Write tools from the laptop: make mi-pg-forward  (then MEETING_INTEL_PG_HOST=127.0.0.1)"
