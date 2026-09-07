#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the Redis Iris Demos repo.
# Installs uv, Python + frontend dependencies, a local Redis server, and a
# baseline .env. Safe to run repeatedly; only creates .env when missing so
# local edits are preserved.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ensuring uv is installed"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
# uv installs to ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"

echo "==> Ensuring a local Redis server is available"
if ! command -v redis-server >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends redis-server
fi

echo "==> Installing Python dependencies (uv sync)"
uv sync

echo "==> Installing frontend dependencies (npm install)"
(cd frontend && npm install)

if [ ! -f .env ]; then
  echo "==> Creating baseline .env (local Redis; blank cloud credentials)"
  cp .env.example .env
  # Point at the local Redis started by .cursor/start.sh.
  sed -i 's/^REDIS_HOST=.*/REDIS_HOST=127.0.0.1/' .env
  sed -i 's/^REDIS_PORT=.*/REDIS_PORT=6379/' .env
  sed -i 's/^REDIS_SSL=.*/REDIS_SSL=false/' .env
  # The OpenAI SDK requires a non-empty key just to construct its client, so the
  # backend cannot import with a blank key. Provide a harmless placeholder; a real
  # OPENAI_API_KEY set as a Cloud Agent secret is injected as an env var and takes
  # precedence over this .env value at runtime.
  sed -i 's/^OPENAI_API_KEY=.*/OPENAI_API_KEY=sk-local-placeholder-not-a-real-key/' .env
else
  echo "==> .env already exists; leaving it untouched"
fi

echo "==> Install complete"
