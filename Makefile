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
# onto argv, never to stdout. The account id is not a secret; Pages' wrangler.toml
# rejects it, so it lives here and in .github/workflows/ci.yml.
CF_ACCOUNT_ID := 76967f5ede1ce50efce34d90b7e94958
CF_ENV    = CLOUDFLARE_ACCOUNT_ID=$(CF_ACCOUNT_ID) CLOUDFLARE_API_TOKEN="$$(sops -d --extract '["cloudflare_pages_token"]' $(SOPS_FILE))"

.DEFAULT_GOAL := help

.PHONY: help install lint format build test check serve drops sold deploy cf-project ci-secrets protect-deploy protect-main audit-deploy secrets clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install locked Python and Tailwind dependencies and the Git LFS hooks
	$(UV) sync --extra dev
	npm ci
	@# Filters only: plain `git lfs install` would write into a global core.hooksPath
	@# dispatcher (lesson-007). The hooks go where the dispatcher chains to.
	git lfs install --local --skip-repo >/dev/null
	@# The repo's own hooks dir, never `git rev-parse --git-path hooks`: that follows
	@# core.hooksPath and would write into the global dispatcher.
	@hooks="$$(git rev-parse --path-format=absolute --git-common-dir)/hooks"; mkdir -p "$$hooks"; \
	for h in pre-push post-checkout post-commit post-merge; do \
		f="$$hooks/$$h"; \
		if [ -e "$$f" ] && ! grep -q 'git lfs' "$$f"; then echo "kept existing non-LFS hook $$f" >&2; continue; fi; \
		printf '#!/bin/sh\ncommand -v git-lfs >/dev/null 2>&1 || { echo >&2 "git-lfs not found on PATH"; exit 2; }\ngit lfs %s "$$@"\n' "$$h" > "$$f"; \
		chmod +x "$$f"; \
	done

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

serve: build ## Serve the catalog and the private tool on 127.0.0.1:$(PORT) (loopback only)
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

protect-deploy: ## Allow deploy secrets only from main, including manual previews
	@set -e; for environment in production preview; do \
		gh api -X PUT "repos/{owner}/{repo}/environments/$$environment" --input .github/deployment-environment.json >/dev/null; \
		policies="repos/{owner}/{repo}/environments/$$environment/deployment-branch-policies"; \
		stale="$$(gh api --paginate "$$policies" --jq '.branch_policies[] | select(.name != "main" or .type != "branch") | .id')"; \
		for policy_id in $$stale; do \
			gh api -X DELETE "$$policies/$$policy_id" >/dev/null; \
		done; \
		main="$$(gh api --paginate "$$policies" --jq '.branch_policies[] | select(.name == "main" and .type == "branch") | .id')"; \
		if [ -z "$$main" ]; then \
			gh api -X POST "$$policies" -f name=main -f type=branch >/dev/null; \
		fi; \
	done

ci-secrets: protect-deploy ## Scope the deploy token and the contact to the protected environments
	@set -e; token="$$(sops -d --extract '["cloudflare_pages_token"]' $(SOPS_FILE))"; \
	test -n "$$token" || { echo "empty Cloudflare token" >&2; exit 1; }; \
	for environment in production preview; do \
		printf '%s' "$$token" | gh secret set CLOUDFLARE_API_TOKEN --env "$$environment"; \
	done; \
	unset token; \
	secrets="$$(gh secret list)"; \
	if printf '%s\n' "$$secrets" | grep -q '^CLOUDFLARE_API_TOKEN[[:space:]]'; then \
		gh secret delete CLOUDFLARE_API_TOKEN; \
	fi; \
	phone="$$(sops -d --extract '["seller"]["phone"]' $(SOPS_FILE))"; \
	test -n "$$phone" || { echo "empty seller phone" >&2; exit 1; }; \
	for environment in production preview; do \
		printf '%s' "$$phone" | gh secret set SELLER_PHONE --env "$$environment"; \
	done; \
	unset phone; \
	secrets="$$(gh secret list)"; \
	if printf '%s\n' "$$secrets" | grep -q '^SELLER_PHONE[[:space:]]'; then \
		gh secret delete SELLER_PHONE; \
	fi

audit-deploy: ## Check the live deploy settings and secrets (read-only)
	scripts/audit-deploy.sh

protect-main: ## Require the CI test check on main (idempotent; admins can still bypass)
	gh api -X PUT repos/{owner}/{repo}/branches/main/protection --input .github/branch-protection.json >/dev/null
	@echo "main requires: $$(gh api repos/{owner}/{repo}/branches/main/protection --jq '[.required_status_checks.contexts[]] | join(", ")')"

secrets: ## Edit the encrypted reserve floors, phone and deploy token
	sops $(SOPS_FILE)

clean: ## Remove build output and caches
	rm -rf build data/inventory.json .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
