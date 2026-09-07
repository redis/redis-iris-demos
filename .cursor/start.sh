#!/usr/bin/env bash
# Per-boot service startup for the Redis Iris Demos Cloud Agent environment.
# Starts a local Redis server if one is not already running. Idempotent.
set -euo pipefail

if redis-cli ping >/dev/null 2>&1; then
  echo "==> Redis already running"
else
  echo "==> Starting local Redis server on 127.0.0.1:6379"
  redis-server --daemonize yes --port 6379 --save "" --appendonly no
  # Wait briefly for readiness.
  for _ in $(seq 1 20); do
    if redis-cli ping >/dev/null 2>&1; then
      echo "==> Redis is ready"
      break
    fi
    sleep 0.5
  done
fi
