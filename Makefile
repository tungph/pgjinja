# Makefile for Python project management

# .PHONY declaration prevents conflicts with files of the same name
.PHONY: install test clean lint format build publish-test publish help

# Install dependencies from requirements.txt if it exists
install:
	@echo "Installing dependencies..."
	@if ! command -v uv &> /dev/null; then \
		echo "Error: uv is not installed. Please install it first (https://github.com/astral-sh/uv)."; \
		exit 1; \
	fi
	@if [ -f requirements.txt ]; then \
		uv sync -r requirements.txt; \
	else \
		echo "No requirements.txt found."; \
	fi

# Run tests using pytest (or your preferred test framework)
test:
	pip uninstall -y pgjinja && pip install -e . && PYTHONPATH=$PYTHONPATH:$(pwd)/src pytest tests/ -v --cov=src/pgjinja

# Clean up compiled Python files and cache directories
clean:
	@echo "Cleaning up Python cache files..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +

# Run code linting with flake8
lint:
	@echo "Running code linting..."
	flake8 .

# Format code using black
format:
	@echo "Formatting code with black..."
	black .

# Build distribution packages
build: clean
	@echo "Building distribution packages..."
	python -m build

# Publish to TestPyPI
publish-test: build
	@echo "Publishing to TestPyPI..."
	@echo "Warning: This will upload the package to TestPyPI. Are you sure? (y/n)"
	@read -r response; \
	if [ "$$response" = "y" ]; then \
		twine upload --repository testpypi dist/*; \
	else \
		echo "Upload cancelled."; \
	fi

# Publish to PyPI
publish: build
	@echo "Publishing to PyPI..."
	@echo "Warning: This will upload the package to PyPI. Make sure you've tested on TestPyPI first. Are you sure? (y/n)"
	@read -r response; \
	if [ "$$response" = "y" ]; then \
		twine upload dist/*; \
	else \
		echo "Upload cancelled."; \
	fi

# Show help information
help:
	@echo "Available targets:"
	@echo "  install - Install Python dependencies from requirements.txt using uv"
	@echo "  test    - Run tests"
	@echo "  clean   - Clean up Python cache files"
	@echo "  lint    - Run code linting with flake8"
	@echo "  format  - Format code with black"
	@echo "  build   - Build distribution packages"
	@echo "  publish-test - Publish package to TestPyPI"
	@echo "  publish - Publish package to PyPI"
	@echo "  help    - Show this help message"
