#!/usr/bin/env bash
# Repoint the RDI Helm release at the live rdidb port.
#
# Redis Enterprise assigns rdidb a random port and picks a new one whenever the
# database is recreated. install-rdi.sh bakes the port that existed at install time
# into Helm values, so after a recreate the processor and collector crash-loop with
# "Timeout connecting to server on rdidb.rdi.svc.cluster.local:<old port>".
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export KUBECONFIG="${KUBECONFIG:-$ROOT/generated/kubeconfig}"
CHART_VERSION="${RDI_CHART_VERSION:-1.14.0}"
CHART_PATH="$ROOT/generated/rdi-${CHART_VERSION}.tgz"

if [[ ! -f "$KUBECONFIG" ]]; then
  echo "No kubeconfig at $KUBECONFIG. Run: gcloud container clusters get-credentials ..."
  exit 2
fi

LIVE_PORT="$(kubectl -n rdi get secret redb-rdidb -o jsonpath='{.data.port}' | base64 --decode)"
LIVE_PASSWORD="$(kubectl -n rdi get secret redb-rdidb -o jsonpath='{.data.password}' | base64 --decode)"
HELM_PORT="$(helm -n rdi get values rdi 2>/dev/null | awk '/^  port:/ {print $2; exit}' | tr -d '"')"

echo "rdidb live port:  $LIVE_PORT"
echo "helm values port: ${HELM_PORT:-<unset>}"

if [[ "$LIVE_PORT" == "$HELM_PORT" ]]; then
  echo "Ports already match. Checking pods..."
  kubectl -n rdi get pods | grep -E 'processor|collector' || true
  exit 0
fi

if [[ ! -f "$CHART_PATH" ]]; then
  echo "Downloading RDI chart ${CHART_VERSION}..."
  curl -L "https://redis-enterprise-software-downloads.s3.amazonaws.com/redis-di/rdi-${CHART_VERSION}.tgz" -o "$CHART_PATH"
fi

echo "Upgrading RDI to port $LIVE_PORT..."
helm upgrade rdi "$CHART_PATH" -n rdi --reuse-values \
  --set connection.port="$LIVE_PORT" \
  --set connection.password="$LIVE_PASSWORD" \
  --wait --timeout 8m

kubectl -n rdi rollout status deploy/processor --timeout=180s
kubectl -n rdi get pods | grep -E 'processor|collector' || true
echo "Done. Verify CDC with: make mi-verify"
