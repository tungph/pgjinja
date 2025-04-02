import logging
from collections.abc import Sequence
from functools import cache
from os import PathLike
from pathlib import Path
from typing import LiteralString

from jinjasql import JinjaSql
from psycopg import OperationalError
from psycopg.conninfo import make_conninfo
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@cache
def _read_text(file: Path) -> str:
    return file.read_text(encoding="utf8")


@cache
def _get_model_fields(model: type) -> str:
    if not issubclass(model, BaseModel):
        raise TypeError(f"{model} is not a subclass of pydantic.BaseModel")

    fields = []
    for name, field_info in model.model_fields.items():
        if alias := field_info.validation_alias:
            fields.append(alias)
        else:
            fields.append(name)
    return ", ".join(fields)


async def _handle_reconnect_failure(pool):
    logger.warning("Reconnection failed, attempting recovery...")
    await pool.close()
    await pool.open()


class PgJinja:
    def __init__(
        self,
        user: str,
        password: str,
        host: str = "localhost",
        port: int = 5432,
        dbname: str = "public",
        template_dir: PathLike | str = Path(),
        max_size: int = 12,
        min_size: int = 1,
        application_name="pgjinja",
    ):
        self.template_dir = Path(template_dir)
        self.db = f"{host}:{port}/{dbname}"

        self.pool = AsyncConnectionPool(
            # ref: https://www.psycopg.org/psycopg3/docs/advanced/pool.html#
            conninfo=make_conninfo(
                # keyword reference: https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                application_name=application_name,
            ),
            reconnect_failed=_handle_reconnect_failure,
            max_size=max_size,
            min_size=min_size,
            open=False,
        )

    def __del__(self):
        del self.pool

    async def _open_pool(self):
        # noinspection PyProtectedMember
        if not self.pool._opened:
            await self.pool.open()
            logger.debug(f"Opened connection pool to {self.db}")

    async def _run(
        self,
        query: LiteralString,
        params: dict | Sequence = (),
        model: type | None = None,
        try_count: int = 0,
    ):
        await self._open_pool()
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
            if try_count == 0 and isinstance(e, OperationalError):
                logger.error(
                    "OperationalError: Connection may be lost. Reconnecting..."
                )
                await _handle_reconnect_failure(self.pool)
                return await self._run(query, params, model, try_count=1)
            raise

    async def query(
        self, template: str, params: dict | None = None, model: type | None = None
    ):
        if params is None:
            params = dict()

        if isinstance(model, type) and issubclass(model, BaseModel):
            params |= dict(_model_fields_=_get_model_fields(model))

        statement = _read_text(self.template_dir / template)
        query, bind_params = JinjaSql(param_style="format").prepare_query(
            statement, params or ()
        )
        return await self._run(query, bind_params, model)
