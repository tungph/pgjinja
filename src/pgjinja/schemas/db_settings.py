from pathlib import Path

from pydantic import BaseModel, SecretStr


class DBSettings(BaseModel):
    """PostgreSQL database connection settings and configuration parameters."""
    host: str = "localhost"
    """Database server hostname or IP address. Defaults to 'localhost'."""

    port: int = 5432
    """PostgreSQL server port. Defaults to 5432."""

    dbname: str = "public"
    """Database name to connect to. Defaults to 'public'."""

    user: str
    """PostgreSQL username for authentication. Required."""

    password: SecretStr
    """PostgreSQL password for authentication. Required."""

    template_dir: Path = Path()
    """Directory containing SQL template files. Defaults to the current directory."""

    min_size: int = 4
    """Minimum number of connections to keep in the connection pool. Defaults to 4."""

    max_size: int | None = None
    """Maximum number of connections allowed in the pool. None means no limit."""

    application_name: str = "pgjinja"
    """Application name to identify this connection in PostgreSQL logs. Defaults to 'pgjinja'."""

    def __repr__(self) -> str:
        """Return a string representation of the DBSettings instance without exposing sensitive information."""
        return f"{self.host}:{self.port}/{self.dbname}"

    @property
    def coninfo(self)->str:
        from psycopg.conninfo import make_conninfo
        return make_conninfo(
            # keyword reference: https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
            host=self.settings.host,
            port=self.settings.port,
            dbname=self.settings.dbname,
            user=self.settings.user,
            password=self.settings.password.get_secret_value(),
            application_name=self.settings.application_name,
        )
