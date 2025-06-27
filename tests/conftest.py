import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel, SecretStr

from pgjinja import DBSettings


@pytest.fixture
def temp_sql_dir():
    """Create a temporary directory with SQL template files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # Create test SQL templates
        (temp_path / "users.sql").write_text(
            "SELECT {{ _model_fields_ }} FROM users WHERE id = {{ user_id }}"
        )
        (temp_path / "insert_user.sql").write_text(
            "INSERT INTO users (name, email) VALUES ({{ name }}, {{ email }})"
        )
        (temp_path / "update_user.sql").write_text(
            "UPDATE users SET name = {{ name }} WHERE id = {{ user_id }}"
        )
        (temp_path / "invalid_template.sql").write_text(
            "SELECT * FROM users WHERE invalid {{ unclosed"
        )

        yield temp_path


@pytest.fixture
def valid_db_settings(temp_sql_dir):
    """Create valid DBSettings for testing."""
    return DBSettings(
        user="testuser",
        password=SecretStr("testpass"),
        host="localhost",
        port=5432,
        dbname="testdb",
        template_dir=temp_sql_dir,
        min_size=1,
        max_size=5,
        application_name="test-app"
    )


@pytest.fixture
def mock_connection():
    """Mock database connection with cursor."""
    mock_conn = Mock()
    mock_cursor = Mock()

    # Setup cursor context manager
    mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)

    # Setup connection context manager
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=None)

    return mock_conn, mock_cursor


@pytest.fixture
def mock_async_connection():
    """Mock async database connection with cursor."""
    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()

    # Create async context manager for cursor
    async def cursor_context():
        class AsyncCursorContext:
            async def __aenter__(self):
                return mock_cursor
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        return AsyncCursorContext()

    # Create async context manager for connection
    async def connection_context():
        class AsyncConnContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        return AsyncConnContext()

    mock_conn.cursor = cursor_context

    return mock_conn, mock_cursor


@pytest.fixture
def sample_user_model():
    """Sample User model for testing."""
    class User(BaseModel):
        id: int
        name: str
        email: str

    return User


@pytest.fixture
def sample_user_with_alias():
    """Sample User model with field aliases."""
    from pydantic import Field

    class UserWithAlias(BaseModel):
        user_id: int = Field(validation_alias="id")
        user_name: str = Field(validation_alias="name")
        user_email: str = Field(validation_alias="email")

    return UserWithAlias


@pytest.fixture
def sample_query_results():
    """Sample query results for testing."""
    return [
        (1, "John Doe", "john@example.com"),
        (2, "Jane Smith", "jane@example.com"),
        (3, "Bob Wilson", "bob@example.com"),
    ]


@pytest.fixture
def sample_cursor_description():
    """Sample cursor description for testing."""
    return [
        ("id", None, None, None, None, None, None),
        ("name", None, None, None, None, None, None),
        ("email", None, None, None, None, None, None),
    ]
