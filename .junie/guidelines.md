# pgjinja Development Guidelines

This document provides essential information for developers working on the pgjinja project. It includes build/configuration instructions, testing information, and additional development details.

## Build and Configuration Instructions

### Environment Setup

1. **Python Version**: pgjinja requires Python 3.11 or higher.

2. **Virtual Environment**: Use uv for dependency management and virtual environment creation:
   ```bash
   uv venv
   . .venv/bin/activate
   ```

3. **Install Dependencies**: Install the project and its dependencies:
   ```bash
   uv sync  # Installs dependencies based on pyproject.toml
   ```

### Building the Package

1. **Build Distribution Packages**:
   ```bash
   uv build
   ```
   This will create wheel and source distribution packages in the `dist/` directory.

2. **Publishing**:
   ```bash
   uv publish --token <PYPI_TOKEN>
   ```

### Configuration

The core configuration for pgjinja is handled through the `DBSettings` class:

```python
from pathlib import Path
from pydantic import SecretStr
from pgjinja import DBSettings

settings = DBSettings(
    user="myuser",
    password=SecretStr("mypassword"),
    host="localhost",
    dbname="mydb",
    template_dir=Path("./templates"),
    min_size=4,  # Default is 4
    max_size=None,  # Default is None (unlimited)
    application_name="my-app"  # Default is "pgjinja"
)
```

## Testing Information

### Running Tests

1. **Run All Tests**:
   ```bash
   make test
   ```
   This will set up a virtual environment, install test dependencies, and run pytest with coverage reporting.

2. **Run Specific Tests**:
   ```bash
   cd src && PYTHONPATH=. pytest ../tests/test_file.py -v
   ```

3. **Run Tests with Coverage**:
   ```bash
   cd src && PYTHONPATH=. pytest ../tests/ -v --cov=pgjinja --cov-report=term-missing
   ```

### Test Organization

- Tests are located in the `tests/` directory
- `conftest.py` contains shared fixtures for tests
- Test files are named with the pattern `test_*.py`
- Test classes are named with the pattern `Test*`
- Test methods are named with the pattern `test_*`

### Adding New Tests

1. **Create a New Test File**: Create a new file in the `tests/` directory with the name pattern `test_*.py`.

2. **Use Fixtures**: Utilize fixtures from `conftest.py` for common test setup.

3. **Example Test**:

```python
import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel, SecretStr

from pgjinja.shared.common import get_model_fields
from pgjinja.schemas.db_settings import DBSettings


class TestExample:
    """Example test class."""

    def test_db_settings_creation(self):
        """Test that DBSettings can be created with valid parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            settings = DBSettings(
                user="testuser",
                password=SecretStr("testpass"),
                host="localhost",
                dbname="testdb",
                template_dir=template_dir
            )

            assert settings.user == "testuser"
            assert settings.password.get_secret_value() == "testpass"
            assert settings.host == "localhost"
            assert settings.dbname == "testdb"
            assert settings.template_dir == template_dir

            # Verify default values
            assert settings.port == 5432
            assert settings.min_size == 4
            assert settings.max_size is None
```

### Test Markers

The project uses the following pytest markers:

- `@pytest.mark.asyncio`: For tests that use asyncio
- `@pytest.mark.integration`: For integration tests

## Additional Development Information

### Code Style

- The project uses ruff for linting and formatting
- Run linting: `ruff check --fix .`
- Run formatting: `ruff format .`
- Line length is set to 88 characters (same as Black)

### Project Structure

- `src/pgjinja/`: Main package code
  - `pgjinja.py`: Synchronous PostgreSQL client
  - `pgjinja_async.py`: Asynchronous PostgreSQL client
  - `schemas/`: Pydantic models for configuration
  - `shared/`: Shared utility functions

### SQL Templates

- SQL templates use Jinja2 syntax
- Templates are stored in a directory specified by `template_dir` in `DBSettings`
- The `_model_fields_` variable is automatically available in templates when a Pydantic model is provided

### Connection Pooling

- The library uses psycopg's connection pooling
- Connections are opened lazily when the first query is executed
- Pool statistics can be accessed via `client.pool.get_stats()`

### Error Handling

- Failed queries are automatically retried up to a configurable number of times
- Exceptions are logged with detailed information about the query, parameters, and pool statistics

### Documentation

- All classes and functions include detailed docstrings with examples
- The README.md file provides comprehensive usage examples
