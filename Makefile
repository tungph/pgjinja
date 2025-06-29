# Makefile for Python project management

# .PHONY declaration prevents conflicts with files of the same name
.PHONY: install test clean lint format lint-format build publish-test publish run-example help default

# Set the default target
.DEFAULT_GOAL := default
# Default target - runs clean, install, format, lint, test in sequence
default: clean install lint test
	@echo "Default sequence completed: clean, install, format, lint, test"

# Install dependencies from requirements.txt if it exists
install:
	uv sync

# Run tests using pytest with proper path setup
test:
	@echo "Setting up and activating virtual environment..."
	@. .venv/bin/activate && \
		uv pip install pytest pytest-asyncio pytest-cov && \
		uv pip install -e . && \
		cd src && \
		PYTHONPATH=. pytest ../tests/ -v \
			--cov=pgjinja \
			--cov-report=term-missing \
			--asyncio-mode=strict \
			|| { echo "Tests failed!"; exit 1; }

# Clean up compiled Python files and cache directories
clean:
	@echo "Cleaning up Python cache files..."
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".coverage" -exec rm -rf {} +
	@find . -type d -name ".tox" -exec rm -rf {} +
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@find . -type d -name "*.egg" -exec rm -rf {} +

lint:
	ruff check --fix .
	ruff format .

# Run both linting and formatting
lint-format: lint format
	@echo "Linting and formatting completed!"

# Build distribution packages
publish: clean
	@echo "Building distribution packages..."
	@uv build
	@echo "Publishing to PyPI..."
	@uv publish --token $(PYPI_TOKEN)
	$(MAKE) clean

# Run the merchant example script
run-example:
	@echo "Running merchant example script..."
	@. .venv/bin/activate && \
		cd examples && PYTHONPATH=.. python merchant_example.py
	@curl -X POST -H 'Content-type: application/json' --data '{"text":"[pgjinja] EXECUTION DONE!"}' https://hooks.slack.com/services/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


# Show help information
help:
	@echo "Available targets:"
	@echo "  install - Install Python dependencies from requirements.txt using uv"
	@echo "  test    - Run tests"
	@echo "  clean   - Clean up Python cache files"
	@echo "  lint    - Run code linting with ruff"
	@echo "  format  - Format code with ruff"
	@echo "  lint-format - Run both linting and formatting with ruff"
	@echo "  build   - Build distribution packages"
	@echo "  publish-test - Publish package to TestPyPI"
	@echo "  publish - Publish package to PyPI"
	@echo "  run-example - Run the merchant example script at ./examples/merchant_example.py"
	@echo "  help    - Show this help message"
