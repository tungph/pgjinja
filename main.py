import asyncio
import logging
from functools import cache

from pydantic import BaseModel

from src.postgres import PostgresAsync

logging.basicConfig(format=">> %(levelname)s %(name)s  %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Merchant(BaseModel):
    id: int
    name: str


@cache
def get_postgres():
    return PostgresAsync(
        user="user",
        password="password",
        host="dev.postgres",
        template_dir="template",
        dbname="dbname",
    )


async def select_merchant(limit: int = 3) -> list[Merchant]:
    params = dict(limit=limit)
    template = "select_merchant.sql.jinja"
    return await get_postgres().query(template, params, Merchant)


async def main():
    merchants = await select_merchant()
    print(merchants)


if __name__ == "__main__":
    asyncio.run(main())
