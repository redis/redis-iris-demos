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
  echo "==> Creating baseline .env"
  cp .env.example .env

  # If no Redis host is provided via a Cloud Agent secret, fall back to the local
  # redis-server that .cursor/start.sh launches. When REDIS_* secrets are present
  # they are injected as env vars and take precedence over these .env values at
  # runtime (load_dotenv does not override existing env vars, and pydantic-settings
  # ranks env vars above the dotenv file), so the app will use Redis Cloud instead.
  if [ -z "${REDIS_HOST:-}" ]; then
    echo "    - no REDIS_HOST secret found; defaulting to local Redis"
    sed -i 's/^REDIS_HOST=.*/REDIS_HOST=127.0.0.1/' .env
    sed -i 's/^REDIS_PORT=.*/REDIS_PORT=6379/' .env
    sed -i 's/^REDIS_SSL=.*/REDIS_SSL=false/' .env
  else
    echo "    - REDIS_HOST secret present; app will use it (local Redis stays idle)"
  fi

  # The OpenAI SDK requires a non-empty key just to *construct* its client, so the
  # backend cannot even import with a blank key. When no OPENAI_API_KEY secret is
  # present, write a harmless placeholder so the app still boots in degraded mode.
  # When the secret is present it is injected as an env var and wins at runtime.
  if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "    - no OPENAI_API_KEY secret found; writing placeholder (degraded mode)"
    sed -i 's/^OPENAI_API_KEY=.*/OPENAI_API_KEY=sk-local-placeholder-not-a-real-key/' .env
  else
    echo "    - OPENAI_API_KEY secret present; app will use it"
  fi
else
  echo "==> .env already exists; leaving it untouched"
fi

echo "==> Install complete"
