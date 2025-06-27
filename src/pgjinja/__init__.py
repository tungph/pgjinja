"""
pgjinja - PostgreSQL with Jinja2 SQL templating library

A library for executing PostgreSQL queries using Jinja2 templates.
Provides a clean separation between SQL and Python code while allowing
for powerful parameterized queries with type safety.

Features:
- Asynchronous PostgreSQL connection handling
- SQL queries as Jinja2 templates
- Type-safe query parameters
- Connection pooling
- Simple API for executing queries and processing results
"""

__version__ = "2.1.0"

from .pgjinja import PgJinja
from .pgjinja_async import PgJinjaAsync
from .schemas.db_settings import DBSettings
from .shared.common import get_model_fields, read_template

# Export common classes and functions
__all__ = [
    "PgJinja",
    "PgJinjaAsync",
    "DBSettings",
    "read_template",
    "get_model_fields",
]
