# =============================================================================
# Makefile – leaving-denver
# `make check` is exactly what CI runs.
# =============================================================================

SHELL := /bin/bash
.SHELLFLAGS := -c -o pipefail

UV      ?= uv
PORT    ?= 8088
PROJECT ?= leaving-denver

.DEFAULT_GOAL := help

.PHONY: help install lint format build test check serve drops sold deploy secrets clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install the locked deps (dev included)
	$(UV) sync --extra dev

lint: ## Ruff lint + format check
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Auto-fix style with ruff
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

build: ## Process photos and compile dist/ (public) + dist_private/ (local only)
	$(UV) run python manage.py build

test: build ## Build, then run the test suite against the fresh build
	$(UV) run pytest

check: lint test ## Lint + build + test (what CI runs)

serve: build ## Serve the catalog and the private tool on localhost:$(PORT)
	$(UV) run python manage.py serve --port $(PORT)

drops: ## Show the staged price-drop table (needs the sops key)
	$(UV) run python manage.py drops

sold: ## Mark an item sold: make sold ID=sofa-sleeper PRICE=200
	@test -n "$(ID)" || { echo "usage: make sold ID=<item-id> [PRICE=<usd>]"; exit 1; }
	$(UV) run python manage.py sold $(ID) $(PRICE)

deploy: check ## Check, then deploy dist/ to Cloudflare Pages from this machine
	npx --yes wrangler pages deploy dist --project-name=$(PROJECT) --branch=main

secrets: ## Edit the encrypted reserve floors / phone
	sops data/private.sops.yaml

clean: ## Remove build output and caches
	rm -rf dist dist_private data/inventory.json .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
