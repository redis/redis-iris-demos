BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8040
FRONTEND_PORT ?= 3040
DOMAIN ?= reddash
EXTRA_ENV_FILE ?=

.PHONY: help install backend-install frontend-install dev backend frontend \
	generate-data generate-models load-data setup-surface validate-domain smoke-domain create-domain flush-redis reset \
	publish-domain-event cache-domain-price-csvs setup \
	mi-pg-up mi-pg-down mi-pg-forward mi-generate-seed mi-rdi-deploy mi-rdi-undeploy mi-rdi-pipeline \
	mi-verify mi-reset mi-embed-sidecar

help:
	@echo "Targets:"
	@echo "  make install          Install backend and frontend dependencies"
	@echo "  make generate-models  Regenerate Context Surface model file for DOMAIN=$(DOMAIN)"
	@echo "  make generate-data    Generate sample JSONL data into output/DOMAIN"
	@echo "  make setup-surface    Create surface & agent key using embedded Redis connection settings"
	@echo "  make load-data        Load output/DOMAIN/*.jsonl into Redis + Search indexes"
	@echo "  make validate-domain  Validate the active domain pack"
	@echo "  make smoke-domain     Generate models/data and verify the domain structure"
	@echo "  make create-domain    Scaffold a new domain pack for DOMAIN=$(DOMAIN)"
	@echo "  make publish-domain-event DOMAIN=<domain>  Publish a random domain live-feed event"
	@echo "  make cache-domain-price-csvs DOMAIN=<domain>  Run a domain-local price cache script when available"
	@echo "    Optional: EXTRA_ENV_FILE=/path/to/shared.env"
	@echo "  make flush-redis      Flush the Redis database (FLUSHDB)"
	@echo "  make reset [DOMAIN=...]  Flush Redis + recreate surface + reload data (DOMAIN defaults to reddash)"
	@echo "  make setup [DOMAIN=...]  Full domain bring-up (RDI path for meeting-intel; JSONL path otherwise)"
	@echo "  make mi-pg-up         Start local meeting-intel Postgres + pgAdmin (optional; GKE has in-cluster Postgres)"
	@echo "  make mi-pg-forward    Port-forward in-cluster Postgres to localhost:5432"
	@echo "  make mi-rdi-deploy    Apply GKE+RDI terraform (requires gcloud)"
	@echo "  make mi-rdi-pipeline  Deploy RDI jobs against the Redis Cloud target"
	@echo "  make mi-verify        Assert Redis key counts match Postgres"
	@echo "  make mi-reset         Re-seed Postgres, reset RDI snapshot, re-verify"
	@echo "  make backend          Start FastAPI backend"
	@echo "  make frontend         Start Vite frontend"
	@echo "  make dev              Run backend and frontend together"

backend-install:
	@uv sync

frontend-install:
	@cd frontend && npm install

install: backend-install frontend-install

generate-models:
	@uv run python scripts/generate_models.py --domain $(DOMAIN)

generate-data:
	@uv run python scripts/generate_data.py --domain $(DOMAIN)

load-data:
	@uv run python scripts/load_data.py --domain $(DOMAIN)

setup-surface:
	@uv run python scripts/setup_surface.py --domain $(DOMAIN)

validate-domain:
	@uv run python scripts/validate_domain.py --domain $(DOMAIN)

smoke-domain:
	@uv run python scripts/smoke_domain.py --domain $(DOMAIN)

create-domain:
	@uv run python scripts/create_domain.py $(DOMAIN)

publish-domain-event:
	@set -a; \
	if [ -f ".env.shared" ]; then . ./.env.shared; fi; \
	if [ -f ".env.local" ]; then . ./.env.local; fi; \
	if [ -n "$(EXTRA_ENV_FILE)" ] && [ -f "$(EXTRA_ENV_FILE)" ]; then . "$(EXTRA_ENV_FILE)"; fi; \
	if [ -f ".env" ]; then . ./.env; fi; \
	if [ ! -f "domains/$(DOMAIN)/publish_random_event.py" ]; then \
		echo "No publish_random_event.py script found for domain '$(DOMAIN)'"; \
		exit 1; \
	fi; \
	uv run python domains/$(DOMAIN)/publish_random_event.py --domain $(DOMAIN)

cache-domain-price-csvs:
	@set -a; \
	if [ -f ".env.shared" ]; then . ./.env.shared; fi; \
	if [ -f ".env.local" ]; then . ./.env.local; fi; \
	if [ -n "$(EXTRA_ENV_FILE)" ] && [ -f "$(EXTRA_ENV_FILE)" ]; then . "$(EXTRA_ENV_FILE)"; fi; \
	if [ -f ".env" ]; then . ./.env; fi; \
	if [ ! -f "domains/$(DOMAIN)/fetch_price_csvs.py" ]; then \
		echo "No fetch_price_csvs.py script found for domain '$(DOMAIN)'"; \
		exit 1; \
	fi; \
	uv run python domains/$(DOMAIN)/fetch_price_csvs.py --years 5

backend:
	@uv run uvicorn backend.app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

frontend:
	@cd frontend && npm run dev -- --host 0.0.0.0 --port $(FRONTEND_PORT)

flush-redis:
	@if [ "$(DOMAIN)" = "meeting-intel" ]; then \
		echo "Refusing to FLUSHDB for meeting-intel: that would wipe RDI-owned keys."; \
		echo "Use 'make mi-reset' (re-seed Postgres + RDI snapshot) instead."; \
		exit 1; \
	fi
	@uv run python -c "\
	from backend.app.settings import get_settings; \
	from backend.app.redis_connection import create_redis_client; \
	s = get_settings(); r = create_redis_client(s); \
	r.flushdb(); \
	print('Flushed Redis at %s:%d/%d' % (s.redis_host, s.redis_port, s.redis_db))"
	@echo ""
	@echo "⚠️  Redis flushed. Context Surface indexes are gone."
	@echo "   Run 'make reset' or 'make setup-surface && make load-data' to recover."

reset:
	@if [ "$(DOMAIN)" = "meeting-intel" ]; then \
		$(MAKE) mi-reset; \
	else \
		$(MAKE) flush-redis DOMAIN=$(DOMAIN); \
		echo "Clearing old surface credentials..."; \
		perl -i -pe 's/^CTX_SURFACE_ID=.*/CTX_SURFACE_ID=/' .env; \
		perl -i -pe 's/^MCP_AGENT_KEY=.*/MCP_AGENT_KEY=/' .env; \
		$(MAKE) setup-surface DOMAIN=$(DOMAIN); \
		$(MAKE) load-data DOMAIN=$(DOMAIN); \
		echo ""; \
		echo "✅ Reset complete. Run 'make dev' to start."; \
	fi

setup:
	@if [ "$(DOMAIN)" = "meeting-intel" ]; then \
		$(MAKE) validate-domain DOMAIN=meeting-intel; \
		$(MAKE) generate-models DOMAIN=meeting-intel; \
		$(MAKE) generate-data DOMAIN=meeting-intel; \
		$(MAKE) mi-rdi-deploy; \
		$(MAKE) mi-rdi-pipeline; \
		$(MAKE) mi-verify; \
		$(MAKE) setup-surface DOMAIN=meeting-intel; \
		uv run python -m scripts.seed_memories; \
		uv run python -m scripts.seed_langcache; \
		echo ""; \
		echo "✅ meeting-intel setup complete. Port-forward Postgres (make mi-pg-forward) so write tools can reach it, then run 'make dev' with DEMO_DOMAIN=meeting-intel."; \
	else \
		$(MAKE) validate-domain DOMAIN=$(DOMAIN); \
		$(MAKE) generate-models DOMAIN=$(DOMAIN); \
		$(MAKE) generate-data DOMAIN=$(DOMAIN); \
		$(MAKE) setup-surface DOMAIN=$(DOMAIN); \
		$(MAKE) load-data DOMAIN=$(DOMAIN); \
		echo ""; \
		echo "✅ Setup complete for DOMAIN=$(DOMAIN). Run 'make dev' to start."; \
	fi

MI_RDI := domains/meeting-intel/rdi
MI_COMPOSE := $(MI_RDI)/source-db/docker-compose.yaml

mi-generate-seed:
	@$(MAKE) generate-data DOMAIN=meeting-intel

mi-pg-up: mi-generate-seed
	@docker compose -f $(MI_COMPOSE) up -d
	@echo "Postgres (Debezium-ready) on localhost:5432  pgAdmin on localhost:8888"

mi-pg-down:
	@docker compose -f $(MI_COMPOSE) down

mi-pg-forward:
	@kubectl --kubeconfig $(MI_RDI)/terraform/generated/kubeconfig -n meeting-intel port-forward svc/postgres 5432:5432

mi-rdi-deploy:
	@cd $(MI_RDI)/terraform && $(MAKE) apply

mi-rdi-undeploy:
	@cd $(MI_RDI)/terraform && $(MAKE) destroy

mi-rdi-pipeline:
	@uv run python domains/meeting-intel/rdi/deploy_pipeline.py

mi-verify:
	@uv run python domains/meeting-intel/rdi/verify.py

mi-reset:
	@$(MAKE) generate-data DOMAIN=meeting-intel
	@uv run python domains/meeting-intel/rdi/reset_pipeline.py
	@$(MAKE) mi-verify

mi-embed-sidecar:
	@uv run python domains/meeting-intel/rdi/embed_sidecar.py

dev:
	@trap 'kill 0' EXIT; $(MAKE) backend & $(MAKE) frontend & wait
