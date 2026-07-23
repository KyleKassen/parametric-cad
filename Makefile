.PHONY: install export-all test lint clean new-part analyze views compare eval \
        spec-init debug-build diff help

PYTHON = uv run python
PYTEST = uv run pytest

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install all dependencies
	uv sync --all-extras
	@echo "\n  ✓ Environment ready. Activate with: source .venv/bin/activate"

export-all: ## Export all parts to exports/ (STEP)
	$(PYTHON) -m lib.export

export-stl: ## Export all parts to exports/ (STEP + STL)
	$(PYTHON) -m lib.export --stl

test: ## Run parametric validation tests
	$(PYTEST) tests/ -v

eval: ## Build -> export -> re-import -> validate -> render -> report -> promote (usage: make eval PART="parts/custom/x")
	$(PYTHON) -m lib.evaluate "$(PART)"

spec-init: ## Draft a spec.json from measured geometry (usage: make spec-init PART="parts/custom/x")
	$(PYTHON) -m lib.evaluate "$(PART)" --init-spec

debug-build: ## Stage-by-stage build bisection (usage: make debug-build PART="parts/custom/x")
	$(PYTHON) -m lib.debug_build "$(PART)"

diff: ## Geometric diff old vs new STEP (usage: make diff A="old.step" B="new.step")
	$(PYTHON) -m lib.diff_step "$(A)" "$(B)"

analyze: ## Exact STEP analysis -> references/ JSON (usage: make analyze FILE="parts/x/part.step")
	$(PYTHON) -m lib.analyze_step "$(FILE)" --save

views: ## Render 6-view + iso verification PNGs (usage: make views FILE="parts/x/part.step")
	$(PYTHON) -m lib.render_step "$(FILE)"

compare: ## Compare two STEP files for identity/mirror (usage: make compare A="a.step" B="b.step")
	$(PYTHON) -m lib.analyze_step --compare "$(A)" "$(B)"

lint: ## Lint and format all Python files
	uv run ruff check --fix .
	uv run ruff format .

clean: ## Remove all generated exports
	find parts -type d -name exports -exec rm -rf {} + 2>/dev/null || true
	@echo "  ✓ Part exports cleaned"

new-part: ## Create a new custom part (usage: make new-part NAME=my_bracket [GROUP=vendor])
ifndef NAME
	$(error NAME is required. Usage: make new-part NAME=my_bracket [GROUP=custom|vendor])
endif
	$(eval GROUP ?= custom)
	@mkdir -p parts/$(GROUP)/$(NAME)/datasheets
	@mkdir -p parts/$(GROUP)/$(NAME)/references
	@echo '{\n    "part_name": "$(NAME)",\n    "version": "v1",\n    "description": "",\n    "units": "mm",\n    "material": "",\n    "process": "",\n    "dimensions": {},\n    "features": {},\n    "notes": []\n}' > parts/$(GROUP)/$(NAME)/params.json
	@cp parts/_template/model.py parts/$(GROUP)/$(NAME)/model.py
	@echo "  ✓ Created parts/$(GROUP)/$(NAME)/"
	@echo "  → Edit parts/$(GROUP)/$(NAME)/params.json with your dimensions"
	@echo "  → Edit parts/$(GROUP)/$(NAME)/model.py with your geometry"
	@echo "  → When it builds: make spec-init PART=parts/$(GROUP)/$(NAME) to draft its acceptance spec"
