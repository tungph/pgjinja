import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel, Field

from pgjinja import DBSettings, PgJinja, PgJinjaAsync


@pytest.mark.integration
class TestPgJinjaIntegration:
    """Integration tests for PgJinja with real template files and model mapping."""

    def test_full_workflow_with_model_fields(self, valid_db_settings, sample_query_results,
                                           sample_cursor_description):
        """Test complete workflow from template to model mapping."""

        # Define test model
        class User(BaseModel):
            id: int
            name: str
            email: str

        client = PgJinja(valid_db_settings)

        # Mock the database interaction
        mock_pool = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()

        mock_pool.connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_pool.connection.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)

        mock_cursor.description = sample_cursor_description
        mock_cursor.fetchall.return_value = sample_query_results

        client.pool = mock_pool

        # Execute query
        result = client.query("users.sql", {"user_id": 1}, User)

        # Verify results
        assert len(result) == 3
        assert all(isinstance(user, User) for user in result)
        assert result[0].id == 1
        assert result[0].name == "John Doe"
        assert result[0].email == "john@example.com"

    def test_template_with_model_fields_substitution(self, valid_db_settings):
        """Test that _model_fields_ is properly substituted in templates."""

        class Product(BaseModel):
            product_id: int = Field(validation_alias="id")
            product_name: str = Field(validation_alias="name")
            price: float

        client = PgJinja(valid_db_settings)

        with patch.object(client, '_run') as mock_run:
            mock_run.return_value = []

            # Call query with model
            client.query("users.sql", {"user_id": 1}, Product)

            # Extract the SQL query that was executed
            args, kwargs = mock_run.call_args
            executed_query = args[0]

            # The query should have the model fields substituted
            assert "id, name, price" in executed_query

    def test_error_propagation_through_stack(self, valid_db_settings):
        """Test that errors propagate correctly through the entire stack."""
        client = PgJinja(valid_db_settings)

        # Mock pool to raise connection error
        mock_pool = Mock()
        mock_pool.connection.side_effect = Exception("Database unavailable")
        mock_pool.get_stats.return_value = {"mock": "stats"}

        client.pool = mock_pool

        with pytest.raises(Exception, match="Database unavailable"):
            client.query("users.sql", {"user_id": 1})

    def test_multiple_template_files_different_operations(self, valid_db_settings):
        """Test using different template files for different operations."""

        class User(BaseModel):
            id: int
            name: str
            email: str

        client = PgJinja(valid_db_settings)

        # Mock different cursor behaviors for different operations
        mock_pool = Mock()
        mock_connection = Mock()

        def mock_cursor_factory():
            cursor = Mock()
            cursor.__enter__ = Mock(return_value=cursor)
            cursor.__exit__ = Mock(return_value=None)
            return cursor

        mock_pool.connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_pool.connection.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value = mock_cursor_factory()

        client.pool = mock_pool

        # Test SELECT operation
        select_cursor = mock_cursor_factory()
        select_cursor.description = [("id", None, None, None, None, None, None),
                                    ("name", None, None, None, None, None, None),
                                    ("email", None, None, None, None, None, None)]
        select_cursor.fetchall.return_value = [(1, "John", "john@example.com")]
        mock_connection.cursor.return_value = select_cursor

        result = client.query("users.sql", {"user_id": 1}, User)
        assert len(result) == 1
        assert isinstance(result[0], User)

        # Test INSERT operation
        insert_cursor = mock_cursor_factory()
        insert_cursor.description = None
        insert_cursor.rowcount = 1
        mock_connection.cursor.return_value = insert_cursor

        result = client.query("insert_user.sql", {"name": "Jane", "email": "jane@example.com"})
        assert result == 1


@pytest.mark.integration
@pytest.mark.asyncio
class TestPgJinjaAsyncIntegration:
    """Integration tests for PgJinjaAsync with real async workflows."""

    async def test_async_full_workflow_with_model_fields(self, valid_db_settings, sample_query_results,
                                                       sample_cursor_description):
        """Test complete async workflow from template to model mapping."""

        # Define test model
        class User(BaseModel):
            id: int
            name: str
            email: str

        client = PgJinjaAsync(valid_db_settings)

        # Mock the async database interaction
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()

        mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_cursor.description = sample_cursor_description
        mock_cursor.fetchall.return_value = sample_query_results

        client.pool = mock_pool

        # Execute async query
        result = await client.query("users.sql", {"user_id": 1}, User)

        # Verify results
        assert len(result) == 3
        assert all(isinstance(user, User) for user in result)
        assert result[0].id == 1
        assert result[0].name == "John Doe"
        assert result[0].email == "john@example.com"

    async def test_async_concurrent_different_templates(self, valid_db_settings):
        """Test concurrent execution of different templates."""
        import asyncio

        class User(BaseModel):
            id: int
            name: str
            email: str

        client = PgJinjaAsync(valid_db_settings)

        # Mock async pool
        mock_pool = AsyncMock()

        async def create_mock_connection():
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()

            mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
            mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

            # Different responses for different queries
            mock_cursor.description = [("id", None, None, None, None, None, None),
                                     ("name", None, None, None, None, None, None),
                                     ("email", None, None, None, None, None, None)]
            mock_cursor.fetchall.return_value = [(1, "User", "user@example.com")]
            mock_cursor.rowcount = 1

            return mock_connection

        mock_pool.connection.return_value.__aenter__ = create_mock_connection
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        client.pool = mock_pool

        # Execute different operations concurrently
        tasks = [
            client.query("users.sql", {"user_id": 1}, User),
            client.query("insert_user.sql", {"name": "New User", "email": "new@example.com"}),
            client.query("update_user.sql", {"user_id": 1, "name": "Updated User"}),
        ]

        results = await asyncio.gather(*tasks)

        # Verify all operations completed
        assert len(results) == 3
        assert isinstance(results[0], list)  # SELECT result
        assert results[1] == 1  # INSERT rowcount
        assert results[2] == 1  # UPDATE rowcount

    async def test_async_error_recovery_across_retries(self, valid_db_settings):
        """Test async error recovery and retry mechanism."""
        client = PgJinjaAsync(valid_db_settings)

        # Mock pool that fails once then succeeds
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()

        mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

        # Fail once, then succeed
        mock_cursor.execute.side_effect = [Exception("Temporary failure"), None]
        mock_cursor.description = None
        mock_cursor.rowcount = 1

        client.pool = mock_pool

        result = await client._run("INSERT INTO users VALUES (%s, %s)", ["test", "test@example.com"], max_retries=2)

        assert result == 1
        assert mock_cursor.execute.call_count == 2


@pytest.mark.integration
class TestEndToEndScenarios:
    """End-to-end scenarios testing complete workflows."""

    def test_sync_async_same_template_different_results(self, valid_db_settings):
        """Test that sync and async versions produce consistent results."""

        class User(BaseModel):
            id: int
            name: str
            email: str

        # Create both clients
        sync_client = PgJinja(valid_db_settings)
        async_client = PgJinjaAsync(valid_db_settings)

        # Mock data
        sample_results = [(1, "John Doe", "john@example.com")]
        sample_description = [("id", None, None, None, None, None, None),
                             ("name", None, None, None, None, None, None),
                             ("email", None, None, None, None, None, None)]

        # Mock sync client
        sync_mock_pool = Mock()
        sync_mock_connection = Mock()
        sync_mock_cursor = Mock()

        sync_mock_pool.connection.return_value.__enter__ = Mock(return_value=sync_mock_connection)
        sync_mock_pool.connection.return_value.__exit__ = Mock(return_value=None)
        sync_mock_connection.cursor.return_value.__enter__ = Mock(return_value=sync_mock_cursor)
        sync_mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)

        sync_mock_cursor.description = sample_description
        sync_mock_cursor.fetchall.return_value = sample_results

        sync_client.pool = sync_mock_pool

        # Execute sync query
        sync_result = sync_client.query("users.sql", {"user_id": 1}, User)

        # Mock async client
        async_mock_pool = AsyncMock()
        async_mock_connection = AsyncMock()
        async_mock_cursor = AsyncMock()

        async_mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=async_mock_connection)
        async_mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)
        async_mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=async_mock_cursor)
        async_mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

        async_mock_cursor.description = sample_description
        async_mock_cursor.fetchall.return_value = sample_results

        async_client.pool = async_mock_pool

        # Execute async query
        import asyncio
        async_result = asyncio.run(async_client.query("users.sql", {"user_id": 1}, User))

        # Compare results
        assert len(sync_result) == len(async_result)
        assert sync_result[0].id == async_result[0].id
        assert sync_result[0].name == async_result[0].name
        assert sync_result[0].email == async_result[0].email

    def test_complex_template_with_conditionals_and_model_fields(self, valid_db_settings):
        """Test complex templates with conditional logic and model field substitution."""

        class UserWithMetadata(BaseModel):
            id: int
            username: str = Field(validation_alias="name")
            email_address: str = Field(validation_alias="email")
            created_at: str
            last_login: str = None

        # Create complex template
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            complex_template = template_dir / "complex_users.sql"
            complex_template.write_text("""
            SELECT {{ _model_fields_ }}
            FROM users u
            LEFT JOIN user_metadata m ON u.id = m.user_id
            WHERE u.id = {{ user_id }}
            {% if include_inactive %}
                OR u.status = 'inactive'
            {% endif %}
            {% if created_after %}
                AND u.created_at > {{ created_after }}
            {% endif %}
            ORDER BY u.created_at DESC
            """)

            # Update settings to use temp dir
            settings = DBSettings(
                user=valid_db_settings.user,
                password=valid_db_settings.password,
                host=valid_db_settings.host,
                port=valid_db_settings.port,
                dbname=valid_db_settings.dbname,
                template_dir=template_dir,
                min_size=valid_db_settings.min_size,
                max_size=valid_db_settings.max_size
            )

            client = PgJinja(settings)

            with patch.object(client, '_run') as mock_run:
                mock_run.return_value = []

                # Execute query with complex parameters
                client.query("complex_users.sql", {
                    "user_id": 1,
                    "include_inactive": True,
                    "created_after": "2023-01-01"
                }, UserWithMetadata)

                # Verify the query was executed
                args, kwargs = mock_run.call_args
                executed_query = args[0]

                # Check that model fields were substituted correctly
                assert "id, name, email, created_at, last_login" in executed_query
                # Check that conditionals were processed
                assert "OR u.status = 'inactive'" in executed_query
                assert "AND u.created_at >" in executed_query
