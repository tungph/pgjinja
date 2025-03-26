"""
Example demonstrating how to use pgjinja for querying merchants from a database.

This example shows the elegant and type-safe approach to database queries
provided by the pgjinja package, using Jinja SQL templates and Pydantic models.
"""

import asyncio
import configparser
import logging
from functools import cache
from pathlib import Path

from pydantic import BaseModel

from src.pgjinja import PgJinja

logging.basicConfig(
    format=">> %(levelname)s %(name)s  %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)


class Merchant(BaseModel):
    """
    Pydantic model representing a merchant.

    Attributes:
        id: The unique identifier for the merchant
        name: The name of the merchant
    """

    id: int
    name: str


@cache
def get_postgres():
    """
    Creates and caches a PostgresAsync instance.

    Uses configuration from config.ini file.

    Returns:
        PgJinja: A configured database connection instance
    """
    # Load configuration from config.ini
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent / "config.ini"
    config.read(config_path)

    db_config = config["database"]
    return PgJinja(
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        dbname=db_config["dbname"],
        template_dir="template",  # Directory containing SQL Jinja templates
    )


async def select_merchant(limit: int = 3) -> list[Merchant]:
    """
    Fetches merchants from the database with optional limit.

    This function demonstrates the elegant way pgjinja handles:
    1. SQL template loading and rendering with parameters
    2. Automatic conversion of query results to Pydantic models
    3. Type safety throughout the query process

    Args:
        limit: Maximum number of merchants to return (default: 3)

    Returns:
        list[Merchant]: A list of Merchant objects from the database
    """
    # Prepare parameters for the SQL template
    params = dict(limit=limit)
    # Specify the template file to use
    template = "select_merchant.sql.jinja"
    # Execute query and automatically convert results to Merchant objects
    return await get_postgres().query(template, params, Merchant)


async def main():
    """
    Main function that demonstrates querying and displaying merchants.
    """
    # Fetch merchants using the convenience function
    merchants = await select_merchant()
    print(merchants)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
