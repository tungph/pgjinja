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

from src.postgres import PostgresAsync


# Create a PostgreSQL connection
@cache
def get_postgres():
    return PostgresAsync(
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

## Configuration

The `PostgresAsync` class accepts the following configuration parameters:

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
- `pydantic` - For data validation and model mapping
- `jinjasql` - For SQL templating with Jinja2
- `psycopg` - PostgreSQL database adapter for Python
- `psycopg_pool` - Connection pooling for psycopg

## License

[MIT License](LICENSE)
