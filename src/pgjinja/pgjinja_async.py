import logging
from collections.abc import Sequence
from typing import LiteralString

from jinjasql import JinjaSql
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from .pgjinja import PgJinja
from .schemas.db_settings import DBSettings
from .shared.common import get_model_fields, read_template

logger = logging.getLogger(__name__)


class PgJinjaAsync(PgJinja):
    """Asynchronous PostgreSQL client with Jinja2 SQL templating.

    PgJinjaAsync provides an async interface for executing PostgreSQL queries
    using Jinja2 templates. It extends PgJinja with asynchronous operations,
    using psycopg3's AsyncConnectionPool for non-blocking database operations.
    The `_model_fields_` feature allows templates to dynamically reference
    model field names for SELECT statements.

    This class is designed for high-concurrency applications where blocking
    database operations would impact performance. All database operations
    are async and use asyncio-compatible connection pooling.

    Args:
        db_settings: Database connection and configuration settings.

    Examples:
        Basic async usage:

        >>> import asyncio
        >>> from pgjinja import PgJinjaAsync, DBSettings
        >>> from pydantic import SecretStr
        >>> 
        >>> async def main():
        ...     settings = DBSettings(
        ...         user="myuser",
        ...         password=SecretStr("mypass"),
        ...         host="localhost",
        ...         dbname="mydb"
        ...     )
        ...     client = PgJinjaAsync(settings)
        ...     result = await client.query("users.sql", {"user_id": 1})
        ...     return result
        >>> asyncio.run(main())

        Using with Pydantic models:

        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     id: int
        ...     name: str
        ...     email: str
        >>> 
        >>> async def get_users():
        ...     client = PgJinjaAsync(settings)
        ...     users = await client.query("users.sql", model=User)
        ...     return users

    Notes:
        - All database operations are asynchronous and must be awaited
        - Connection pool is async-safe and handles concurrent requests
        - Pool connections are opened lazily on first query execution
        - Failed queries are automatically retried up to max_retries times
        - When using Pydantic models, `_model_fields_` is automatically
          available in templates containing comma-separated field names
    """

    def __init__(self, db_settings: DBSettings):
        """Initialize PgJinjaAsync with database settings and async connection
        pool.

        Creates a new PgJinjaAsync instance with the provided database configuration.
        The async connection pool is created but not opened until the first query
        is executed (lazy initialization). Pool connections are managed
        automatically and are asyncio-compatible for concurrent operations.

        Args:
            db_settings: Database connection and configuration settings including
                connection parameters (host, port, user, password, database),
                connection pool sizing (min_size, max_size), template directory
                location, and other connection options.

        Examples:
            Basic instantiation with DBSettings:

            >>> from pgjinja import PgJinjaAsync, DBSettings
            >>> from pydantic import SecretStr
            >>> settings = DBSettings(
            ...     user="postgres",
            ...     password=SecretStr("mypassword"),
            ...     host="localhost",
            ...     port=5432,
            ...     dbname="myapp",
            ...     min_size=2,
            ...     max_size=20  # Higher for async workloads
            ... )
            >>> client = PgJinjaAsync(settings)

            With custom template directory for async operations:

            >>> from pathlib import Path
            >>> settings = DBSettings(
            ...     user="postgres",
            ...     password=SecretStr("mypassword"),
            ...     host="localhost",
            ...     dbname="myapp",
            ...     template_dir=Path("./async_sql_templates"),
            ...     max_size=25  # Higher pool size for concurrency
            ... )
            >>> client = PgJinjaAsync(settings)

        Notes:
            - Async connection pool is not opened during initialization for performance
            - Pool configuration (min_size, max_size) is crucial for async concurrent handling
            - Template directory from settings is used to resolve template file paths
            - Pool is asyncio-compatible and safe for concurrent async operations
        """
        super().__init__(db_settings)

        self.pool = AsyncConnectionPool(
            conninfo=self.settings.coninfo,
            max_size=self.settings.max_size,
            min_size=self.settings.min_size,
            open=False,
        )

    async def _open_pool(self):
        # noinspection PyProtectedMember
        if not self.pool._opened:
            await self.pool.open()
            logger.debug(f"Opened connection pool to {self.settings}")

    async def _run(
        self,
        query: LiteralString,
        params: dict | Sequence = (),
        model: type | None = None,
        max_retries: int = 2,
    ):
        await self._open_pool()
        attempts = 0
        while attempts < max_retries:
            try:
                async with (
                    self.pool.connection() as connection,
                    connection.cursor() as cursor,
                ):
                    await cursor.execute(query, params)
                    if cursor.description:
                        if model is not None:
                            headers = [desc[0] for desc in cursor.description]
                            rows = await cursor.fetchall()
                            mapped_rows = [dict(zip(headers, r)) for r in rows]
                            return [model(**r) for r in mapped_rows]
                        else:
                            return await cursor.fetchall()

                    return cursor.rowcount
            except Exception as e:
                stats = self.pool.get_stats()
                logger.exception(
                    f"PgJinja Exception: {e}"
                    f"\nQuery: {query}"
                    f"\nParams: {params}"
                    f"\nModel: {model}"
                    f"\nPool Stats: {stats}"
                )

                attempts += 1
                if attempts >= max_retries:
                    raise
                logger.warning(f"Retrying query ({attempts}/{max_retries})...")

    async def query(
        self, template: str, params: dict | None = None, model: type | None = None
    ):
        """Asynchronously execute a SQL query from a Jinja2 template file.

        Loads and renders a Jinja2 SQL template with the provided parameters,
        then executes the resulting query against PostgreSQL using async
        operations. When a Pydantic model is provided, query results are
        automatically mapped to model instances and `_model_fields_` is made
        available in the template.

        Args:
            template: Path to the SQL template file relative to template_dir.
            params: Dictionary of parameters to pass to the Jinja2 template.
                Defaults to empty dict if None.
            model: Optional Pydantic BaseModel class for automatic result
                mapping. When provided, `_model_fields_` containing
                comma-separated field names is added to template context.

        Returns:
            list[BaseModel] | list[tuple] | int: For SELECT queries with model,
                returns list of model instances. For SELECT queries without
                model, returns list of tuples. For INSERT/UPDATE/DELETE
                queries, returns number of affected rows.

        Raises:
            FileNotFoundError: If the template file does not exist.
            psycopg.Error: For PostgreSQL-specific errors (connection,
                syntax, constraint violations, etc.).
            jinjasql.InvalidQuery: If the template cannot be rendered or
                contains invalid SQL after parameter substitution.
            pydantic.ValidationError: If model validation fails during
                result mapping.
            TypeError: If model is not a Pydantic BaseModel subclass.

        Examples:
            Simple async query without model:

            >>> async def get_data():
            ...     client = PgJinjaAsync(settings)
            ...     rows = await client.query("users.sql", {"min_age": 18})
            ...     return rows

            Async query with Pydantic model mapping:

            >>> class User(BaseModel):
            ...     id: int
            ...     name: str
            >>> 
            >>> async def get_users():
            ...     client = PgJinjaAsync(settings)
            ...     users = await client.query("users.sql", {"min_age": 18}, User)
            ...     return users

            Using _model_fields_ in template:

            >>> # In users.sql template:
            >>> # SELECT {{ _model_fields_ }} FROM users WHERE age >= {{ min_age }}
            >>> async def get_typed_users():
            ...     client = PgJinjaAsync(settings)
            ...     users = await client.query("users.sql", {"min_age": 18}, User)
            ...     return users

        Notes:
            - Template file paths are relative to DBSettings.template_dir
            - Connection pool is opened automatically if not already open
            - Failed queries are retried up to 2 times by default
            - All operations are non-blocking and asyncio-compatible
        """
        if params is None:
            params = dict()

        if isinstance(model, type) and issubclass(model, BaseModel):
            params |= dict(_model_fields_=get_model_fields(model))

        statement = read_template(self.settings.template_dir / template)
        query, bind_params = JinjaSql(param_style="format").prepare_query(
            statement, params or ()
        )
        return await self._run(query, bind_params, model)
