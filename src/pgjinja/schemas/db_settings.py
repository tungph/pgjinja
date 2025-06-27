from pathlib import Path

from pydantic import BaseModel, SecretStr


class DBSettings(BaseModel):
    """PostgreSQL database connection settings and configuration parameters.

    This Pydantic model encapsulates all settings required for establishing
    PostgreSQL connections and configuring connection pooling. It provides
    validation for connection parameters and generates connection strings
    compatible with psycopg3.

    The class handles sensitive information like passwords using Pydantic's
    SecretStr type to prevent accidental logging or exposure.

    Attributes:
        host: Database server hostname or IP address.
        port: PostgreSQL server port number.
        dbname: Target database name.
        user: PostgreSQL username for authentication.
        password: PostgreSQL password (stored securely as SecretStr).
        template_dir: Directory path containing SQL template files.
        min_size: Minimum connections to maintain in the pool.
        max_size: Maximum connections allowed in the pool (None = unlimited).
        application_name: Name identifier for this connection in PostgreSQL logs.

    Examples:
        Basic connection settings:

        >>> from pydantic import SecretStr
        >>> from pathlib import Path
        >>> settings = DBSettings(
        ...     user="myuser",
        ...     password=SecretStr("mypass"),
        ...     host="localhost",
        ...     dbname="mydb",
        ...     template_dir=Path("./templates")
        ... )
        >>> print(settings)  # Password is hidden
        localhost:5432/mydb

        With custom pooling settings:

        >>> settings = DBSettings(
        ...     user="myuser",
        ...     password=SecretStr("mypass"),
        ...     host="db.example.com",
        ...     port=5433,
        ...     dbname="production",
        ...     min_size=10,
        ...     max_size=50,
        ...     application_name="my-app"
        ... )

    Notes:
        - Password is automatically secured using Pydantic SecretStr
        - Connection info is generated lazily via the coninfo property
        - String representation excludes sensitive information
    """

    host: str = "localhost"
    """Database server hostname or IP address.

    Defaults to 'localhost'.
    """

    port: int = 5432
    """PostgreSQL server port.

    Defaults to 5432.
    """

    dbname: str = "public"
    """Database name to connect to.

    Defaults to 'public'.
    """

    user: str
    """PostgreSQL username for authentication.

    Required.
    """

    password: SecretStr
    """PostgreSQL password for authentication.

    Required.
    """

    template_dir: Path = Path()
    """Directory containing SQL template files.

    Defaults to the current directory.
    """

    min_size: int = 4
    """Minimum number of connections to keep in the connection pool.

    Defaults to 4.
    """

    max_size: int | None = None
    """Maximum number of connections allowed in the pool.

    None means no limit.
    """

    application_name: str = "pgjinja"
    """Application name to identify this connection in PostgreSQL logs.

    Defaults to 'pgjinja'.
    """

    def __repr__(self) -> str:
        return f"{self.host}:{self.port}/{self.dbname}"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def coninfo(self) -> str:
        """Generate PostgreSQL connection string for psycopg3.

        Creates a properly formatted connection string using psycopg3's
        make_conninfo function. This includes all necessary connection
        parameters including the decoded password from SecretStr.

        Returns:
            str: PostgreSQL connection string suitable for psycopg3
                ConnectionPool or AsyncConnectionPool.

        Examples:
            >>> settings = DBSettings(
            ...     user="myuser",
            ...     password=SecretStr("mypass"),
            ...     host="localhost",
            ...     dbname="mydb"
            ... )
            >>> connstr = settings.coninfo
            >>> print(connstr)
            host=localhost port=5432 dbname=mydb user=myuser password=mypass

        Notes:
            - Password is securely extracted from SecretStr
            - Uses psycopg3's make_conninfo for proper escaping
            - Connection string format follows PostgreSQL standards
        """
        from psycopg.conninfo import make_conninfo

        return make_conninfo(
            # keyword reference: https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password.get_secret_value(),
            application_name=self.application_name,
        )
