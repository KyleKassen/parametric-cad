.PHONY: install export-all test lint clean new-part help

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

lint: ## Lint and format all Python files
	uv run ruff check --fix .
	uv run ruff format .

clean: ## Remove all generated exports
	find parts -type d -name exports -exec rm -rf {} + 2>/dev/null || true
	@echo "  ✓ Part exports cleaned"

new-part: ## Create a new part directory (usage: make new-part NAME=my_bracket)
ifndef NAME
	$(error NAME is required. Usage: make new-part NAME=my_bracket)
endif
	@mkdir -p parts/$(NAME)/datasheets
	@mkdir -p parts/$(NAME)/references
	@echo '{\n    "part_name": "$(NAME)",\n    "version": "v1",\n    "description": "",\n    "units": "mm",\n    "material": "",\n    "process": "",\n    "dimensions": {},\n    "features": {},\n    "notes": []\n}' > parts/$(NAME)/params.json
	@cp parts/example_part/model.py parts/$(NAME)/model.py
	@echo "  ✓ Created parts/$(NAME)/"
	@echo "  → Edit parts/$(NAME)/params.json with your dimensions"
	@echo "  → Edit parts/$(NAME)/model.py with your geometry"
