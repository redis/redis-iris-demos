BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8040
FRONTEND_PORT ?= 3040
EXTRA_ENV_FILE ?=

# GNU sed rejects `sed -i ''`; BSD sed requires it. Both accept `-i.bak`.
SED_INPLACE = sed -i.bak

# Active domain: reads DEMO_DOMAIN from .env automatically.
# Override with: make <target> DOMAIN=electrohub
DOMAIN ?= $(or $(shell grep -s '^DEMO_DOMAIN=' .env | cut -d= -f2),reddash)

.PHONY: help domains setup reset dev backend frontend install \
	backend-install frontend-install \
	generate-models generate-data setup-surface load-data \
	seed-memories seed-langcache seed-all flush-redis \
	validate-domain smoke-domain create-domain \
	publish-domain-event cache-domain-price-csvs \
	mi-pg-up mi-pg-down mi-pg-forward mi-generate-seed mi-rdi-deploy mi-rdi-undeploy mi-rdi-pipeline \
	mi-verify mi-reset mi-embed-sidecar

help:
	@echo ""
	@echo "  make domains            Show available domains"
	@echo "  make setup [DOMAIN=X]   Full setup (first time or switch domain)"
	@echo "  make reset              Reload data for current domain"
	@echo "  make dev                Start backend + frontend"
	@echo ""
	@echo "  make install            Install Python + JS dependencies"
	@echo "  make seed-memories      Re-seed long-term memories"
	@echo "  make seed-langcache     Re-seed LangCache entries"
	@echo "  make flush-redis        Wipe Redis (refused for meeting-intel)"
	@echo "  make mi-rdi-deploy      Apply GKE+RDI terraform for Minutes"
	@echo "  make mi-verify          Postgres vs Redis prefix counts + CDC probe"
	@echo ""
	@echo "  Active domain: $(DOMAIN)"
	@echo ""

domains:
	@echo ""
	@echo "Available domains:"
	@echo ""
	@for d in domains/*/domain.py; do \
		name=$$(basename $$(dirname $$d)); \
		if [ "$$name" = "$(DOMAIN)" ]; then \
			printf "  %-25s <- active\n" "$$name"; \
		else \
			printf "  %-25s\n" "$$name"; \
		fi; \
	done
	@echo ""
	@echo "Switch: make setup DOMAIN=<name>"
	@echo ""

setup:
	@if [ ! -f .env ]; then echo "No .env file. Run: cp .env.example .env"; exit 1; fi
	@if [ "$(DOMAIN)" = "meeting-intel" ]; then \
		echo "Setting up meeting-intel (RDI path)..."; \
		$(SED_INPLACE) 's/^DEMO_DOMAIN=.*/DEMO_DOMAIN=$(DOMAIN)/' .env && rm -f .env.bak; \
		$(MAKE) validate-domain DOMAIN=meeting-intel; \
		$(MAKE) generate-models DOMAIN=meeting-intel; \
		$(MAKE) generate-data DOMAIN=meeting-intel; \
		$(MAKE) mi-rdi-deploy; \
		$(MAKE) mi-rdi-pipeline; \
		$(MAKE) mi-verify; \
		$(MAKE) setup-surface DOMAIN=meeting-intel; \
		DEMO_DOMAIN=meeting-intel uv run python -m scripts.seed_memories; \
		DEMO_DOMAIN=meeting-intel uv run python -m scripts.seed_langcache; \
		echo ""; \
		echo "Done. Port-forward Postgres (make mi-pg-forward), then make dev."; \
	else \
		echo "Setting up $(DOMAIN)..."; \
		echo ""; \
		$(SED_INPLACE) 's/^DEMO_DOMAIN=.*/DEMO_DOMAIN=$(DOMAIN)/' .env && rm -f .env.bak; \
		uv run python scripts/generate_models.py --domain $(DOMAIN); \
		uv run python scripts/generate_data.py --domain $(DOMAIN); \
		uv run python scripts/flush_redis.py; \
		$(SED_INPLACE) 's/^CTX_SURFACE_ID=.*/CTX_SURFACE_ID=/' .env && rm -f .env.bak; \
		$(SED_INPLACE) 's/^MCP_AGENT_KEY=.*/MCP_AGENT_KEY=/' .env && rm -f .env.bak; \
		uv run python scripts/setup_surface.py --domain $(DOMAIN); \
		uv run python scripts/load_data.py --domain $(DOMAIN); \
		DEMO_DOMAIN=$(DOMAIN) uv run python -m scripts.seed_memories; \
		DEMO_DOMAIN=$(DOMAIN) uv run python -m scripts.seed_langcache; \
		echo ""; \
		echo "Done. Run 'make dev' to start."; \
	fi

reset:
	@if [ "$(DOMAIN)" = "meeting-intel" ]; then \
		$(MAKE) mi-reset; \
	else \
		echo "Reloading $(DOMAIN)..."; \
		echo ""; \
		uv run python scripts/generate_data.py --domain $(DOMAIN); \
		uv run python scripts/flush_redis.py; \
		$(SED_INPLACE) 's/^CTX_SURFACE_ID=.*/CTX_SURFACE_ID=/' .env && rm -f .env.bak; \
		$(SED_INPLACE) 's/^MCP_AGENT_KEY=.*/MCP_AGENT_KEY=/' .env && rm -f .env.bak; \
		uv run python scripts/setup_surface.py --domain $(DOMAIN); \
		uv run python scripts/load_data.py --domain $(DOMAIN); \
		DEMO_DOMAIN=$(DOMAIN) uv run python -m scripts.seed_memories; \
		DEMO_DOMAIN=$(DOMAIN) uv run python -m scripts.seed_langcache; \
		echo ""; \
		echo "Done. Run 'make dev' to start."; \
	fi

# --- Individual steps ---

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
	@uv run python -m uvicorn backend.app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

frontend:
	@cd frontend && npm run dev -- --host 0.0.0.0 --port $(FRONTEND_PORT)

flush-redis:
	@if [ "$(DOMAIN)" = "meeting-intel" ]; then \
		echo "Refusing to FLUSHDB for meeting-intel: that would wipe RDI-owned keys."; \
		echo "Use 'make mi-reset' (re-seed Postgres + RDI snapshot) instead."; \
		exit 1; \
	fi
	@uv run python scripts/flush_redis.py

seed-memories:
	@DEMO_DOMAIN=$(DOMAIN) uv run python -m scripts.seed_memories

seed-langcache:
	@DEMO_DOMAIN=$(DOMAIN) uv run python -m scripts.seed_langcache

seed-all: seed-memories seed-langcache

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
	@lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || true
	@lsof -ti:$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	@trap 'kill 0' EXIT; $(MAKE) backend & $(MAKE) frontend & wait
