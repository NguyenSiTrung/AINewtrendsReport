.PHONY: install dev lint format typecheck test pre-commit clean

install:  ## Install production dependencies
	uv sync --no-dev

dev:  ## Install all dependencies (including dev)
	uv sync

lint:  ## Run ruff linter
	uv run ruff check .
	uv run ruff format --check .

format:  ## Auto-format code
	uv run ruff check --fix .
	uv run ruff format .

typecheck:  ## Run mypy type checker
	uv run mypy src/

test:  ## Run tests with coverage
	uv run pytest --cov

pre-commit:  ## Run pre-commit on all files
	uv run pre-commit run --all-files

clean:  ## Remove build artifacts and caches
	rm -rf .mypy_cache .ruff_cache .pytest_cache
	rm -rf dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
