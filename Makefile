# =============================================================================
# Makefile – leaving-denver
# `make check` is exactly what CI runs.
# =============================================================================

SHELL := /bin/bash
.SHELLFLAGS := -c -o pipefail

UV      ?= uv
PORT    ?= 8088
PROJECT ?= leaving-denver
# Where `make deploy` publishes. Anything but main is a preview deployment
# (<branch>.<project>.pages.dev); main is the live site.
BRANCH  ?= preview

SOPS_FILE := data/private.sops.yaml
WRANGLER  := npx --yes wrangler@4.141.0
# The deploy token goes from sops straight into wrangler's environment: never
# onto argv, never to stdout. The account id comes from wrangler.toml.
CF_ENV    := CLOUDFLARE_API_TOKEN="$$(sops -d --extract '["cloudflare_pages_token"]' $(SOPS_FILE))"

.DEFAULT_GOAL := help

.PHONY: help install lint format build test check serve drops sold deploy cf-project ci-secrets protect-main secrets clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install the locked deps (dev included)
	$(UV) sync --extra dev

lint: ## Ruff lint + format check
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Auto-fix style with ruff
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

build: ## Process photos and compile build/public/ (public) + build/private/ (local only)
	$(UV) run leaving-denver build

test: build ## Build, then run the test suite against the fresh build
	$(UV) run pytest

check: lint test ## Lint + build + test (what CI runs)

serve: build ## Serve the catalog and the private tool on localhost:$(PORT)
	$(UV) run leaving-denver serve --port $(PORT)

drops: ## Show the staged price-drop table (needs the sops key)
	$(UV) run leaving-denver drops

sold: ## Mark an item sold: make sold ID=sofa-sleeper PRICE=200
	@test -n "$(ID)" || { echo "usage: make sold ID=<item-id> [PRICE=<usd>]"; exit 1; }
	$(UV) run leaving-denver sold $(ID) $(PRICE)

deploy: check ## Check, then deploy build/public/ from this machine (BRANCH=main goes live)
	$(CF_ENV) $(WRANGLER) pages deploy --project-name=$(PROJECT) --branch=$(BRANCH)

cf-project: ## Create the Cloudflare Pages project if it does not exist (idempotent)
	@if $(CF_ENV) $(WRANGLER) pages project list 2>/dev/null | grep -qw '$(PROJECT)'; then \
		echo "Pages project $(PROJECT) already exists"; \
	else \
		$(CF_ENV) $(WRANGLER) pages project create $(PROJECT) --production-branch=main --force; \
	fi

ci-secrets: ## Push the CI secrets from the sops file to GitHub (values never printed)
	@set -e; for pair in 'CLOUDFLARE_API_TOKEN=["cloudflare_pages_token"]' 'SELLER_PHONE=["seller"]["phone"]'; do \
		name=$${pair%%=*}; value="$$(sops -d --extract "$${pair#*=}" $(SOPS_FILE))"; \
		test -n "$$value" || { echo "empty value for $$name" >&2; exit 1; }; \
		printf '%s' "$$value" | gh secret set "$$name"; \
	done

protect-main: ## Require the CI test check on main (idempotent; admins can still bypass)
	gh api -X PUT repos/{owner}/{repo}/branches/main/protection --input .github/branch-protection.json >/dev/null
	@echo "main requires: $$(gh api repos/{owner}/{repo}/branches/main/protection --jq '[.required_status_checks.contexts[]] | join(", ")')"

secrets: ## Edit the encrypted reserve floors, phone and deploy token
	sops $(SOPS_FILE)

clean: ## Remove build output and caches
	rm -rf build data/inventory.json .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
