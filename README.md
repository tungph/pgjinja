# pgjinja

A Python library that combines PostgreSQL with Jinja2 templates to create dynamic SQL queries with a
clean, async interface.

## Description

pgjinja simplifies database interactions by allowing you to:

- Keep SQL queries in separate template files
- Use Jinja2 templating for dynamic query generation
- Execute queries asynchronously
- Automatically map query results to Pydantic models

This approach helps separate SQL logic from application code, making your database interactions more
maintainable and testable.

## Installation

```bash
pip install pgjinja
```

## Usage Example

Here's a simple example of how to use pgjinja to query merchants from a database:

```python
# src/my_db.py
from functools import cache

from src.models.merchant import Merchant

from pgjinja import PgJinja


# Create a PostgreSQL connection
@cache
def get_postgres():
    return PgJinja(
        user="user",
        password="password",
        host="dev.postgres",
        template_dir="template",
        dbname="dbname",
    )


# Query using a template with parameters
async def select_merchant(limit: int = 3) -> list[Merchant]:
    params = dict(limit=limit)
    template = "select_merchant.sql.jinja"
    return await get_postgres().query(template, params, Merchant)

# Add other database operations here
# ...
```

```python
# main.py
import asyncio

import src.my_db as db


# Example usage
async def main():
    merchants = await db.select_merchant(limit=5)  # clean and very readable
    # Even with a more complex query, the interface is still the same

    print(merchants)


if __name__ == "__main__":
    asyncio.run(main())
```

### SQL Template Example

Create a file `template/select_merchant.sql.jinja`:

```sql
SELECT id, name
FROM merchants
WHERE active = true
ORDER BY name
LIMIT {{ limit }}
```

### Model-Driven Field Selection with Pydantic[Beta]

pgjinja provides a convenient feature called `_model_fields_` that automatically extracts fields from Pydantic models for use in your SQL templates. This helps maintain consistency between your data models and SQL queries.

When you pass a Pydantic model class to the `query()` method, pgjinja automatically:
1. Makes all model fields available in templates via the `_model_fields_` variable
2. Creates a comma-separated list of field names that you can use directly in SELECT statements

This feature is compatible with both Pydantic v1 and v2.

#### Example with Auto Field Selection

Here's how to use the `_model_fields_` feature in your SQL templates:

```sql
-- template/select_merchant_with_model_fields.sql.jinja
SELECT {{ _model_fields_ }}
FROM merchants
WHERE active = true
ORDER BY name
LIMIT {{ limit }}
```

With this template, you can use the same Python code:

```python
async def select_merchant(limit: int = 3) -> list[Merchant]:
    params = dict(limit=limit)
    template = "select_merchant_with_model_fields.sql.jinja"
    return await get_postgres().query(template, params, Merchant)
```

If your `Merchant` model has fields like `id`, `name`, `created_at`, etc., the SQL query will automatically become:

```sql
SELECT id, name, created_at, ...
FROM merchants
WHERE active = true
ORDER BY name
LIMIT 3
```

This approach ensures your SQL queries always match your model fields, even when you add or remove fields from your Pydantic models.

## Configuration

The `PgJinja` class accepts the following configuration parameters:

| Parameter          | Description                                | Default           |
|--------------------|--------------------------------------------|-------------------|
| user               | PostgreSQL user                            | (Required)        |
| password           | PostgreSQL password                        | (Required)        |
| host               | Database host                              | localhost         |
| port               | Database port                              | 5432              |
| dbname             | Database name                              | public            |
| template_dir       | Directory containing SQL templates         | Current directory |
| template_extension | File extension to append to template names | Empty string      |

## Asynchronous Execution and Connection Pooling

pgjinja leverages modern Python's async capabilities and PostgreSQL connection pooling for optimal
performance:

- **Async/await pattern**: All database operations use the async/await pattern for non-blocking
  execution
- **Connection pooling**: Built-in connection pooling via `psycopg_pool` reduces connection overhead
- **Resource management**: Connections are automatically returned to the pool after query execution
- **Concurrent queries**: Multiple queries can be executed concurrently without blocking the main
  thread

This approach is particularly beneficial for web applications and API services where database
operations should not block the event loop while waiting for results.

## Dependencies

- `asyncio` - For asynchronous operations
- `pydantic` - For data validation and model mapping (compatible with both Pydantic v1 and v2)
- `jinjasql2` - For SQL templating with Jinja2
- `psycopg` - PostgreSQL database adapter for Python
- `psycopg_pool` - Connection pooling for psycopg

## Development and Testing

### Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/tungph/pgjinja.git
   cd pgjinja
   ```

2. Create and activate a virtual environment:
   ```bash
   uv venv
   . .venv/bin/activate
   ```

3. Install development dependencies:
   ```bash
   uv pip install pytest pytest-asyncio pytest-cov
   pip install -e .
   ```

### Running Tests

To run the test suite:

```bash
make test
```

This will:

- Set up a virtual environment
- Install necessary test dependencies
- Run the tests with code coverage reporting

## License

[MIT License](LICENSE)
