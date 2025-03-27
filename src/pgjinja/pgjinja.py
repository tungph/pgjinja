import logging
from collections.abc import Sequence
from functools import cache
from os import PathLike
from pathlib import Path
from typing import LiteralString

from jinjasql import JinjaSql
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


class PgJinja:
    def __init__(
        self,
        user: str,
        password: str,
        host: str = "localhost",
        port: int = 5432,
        dbname: str = "public",
        template_dir: PathLike | str = Path(),
    ):
        self.template_dir = Path(template_dir)
        self.db = f"{host}:{port}/{dbname}"

        self.pool = AsyncConnectionPool(
            conninfo=make_conninfo(
                # keyword reference: https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
            ),
            open=False,
        )

        self._is_pool_open = False

    def __del__(self):
        del self.pool

    async def _open_pool(self):
        if not self._is_pool_open:
            await self.pool.open()
            logger.debug(f"Opened connection pool to {self.db}")
            self._is_pool_open = True

    async def _run(
        self,
        query: LiteralString,
        params: dict | Sequence = (),
        model: type | None = None,
    ):
        await self._open_pool()
        async with self.pool.connection() as connection, connection.cursor() as cursor:
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
