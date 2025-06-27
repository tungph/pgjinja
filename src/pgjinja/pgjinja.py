import logging
from collections.abc import Sequence
from typing import LiteralString

from jinjasql import JinjaSql
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

from .schemas.db_settings import DBSettings
from .shared.common import get_model_fields, read_template

logger = logging.getLogger(__name__)


class PgJinja:
    def __init__(self, db_settings: DBSettings):
        self.settings = db_settings
        self.pool = ConnectionPool(
            # ref: https://www.psycopg.org/psycopg3/docs/advanced/pool.html#
            conninfo=self.settings.coninfo,
            max_size=self.settings.max_size,
            min_size=self.settings.min_size,
            open=False,
        )

    def __del__(self):
        if hasattr(self, 'pool'):
            self.pool.close()

    def _open_pool(self):
        # noinspection PyProtectedMember
        if not self.pool._opened:
            self.pool.open()
            logger.debug(f"Opened connection pool to {self.settings}")

    def _run(
        self,
        query: LiteralString,
        params: dict | Sequence = (),
        model: type | None = None,
        max_retries: int = 2,
    ):
        self._open_pool()
        attempts = 0
        while attempts < max_retries:
            try:
                with (
                    self.pool.connection() as connection,
                    connection.cursor() as cursor,
                ):
                    cursor.execute(query, params)
                    if cursor.description:
                        if model is not None:
                            headers = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            mapped_rows = [dict(zip(headers, r)) for r in rows]
                            return [model(**r) for r in mapped_rows]
                        else:
                            return cursor.fetchall()

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

    def query(
        self, template: str, params: dict | None = None, model: type | None = None
    ):
        if params is None:
            params = dict()

        if isinstance(model, type) and issubclass(model, BaseModel):
            params |= dict(_model_fields_=get_model_fields(model))

        statement = read_template(self.settings.template_dir / template)
        query, bind_params = JinjaSql(param_style="format").prepare_query(
            statement, params or ()
        )
        return self._run(query, bind_params, model)
