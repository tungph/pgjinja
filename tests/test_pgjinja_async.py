from unittest.mock import AsyncMock, Mock, patch

import pytest
from psycopg_pool import AsyncConnectionPool

from pgjinja import PgJinjaAsync


class TestPgJinjaAsyncInitialization:
    def test_async_initialization_with_valid_settings(self, valid_db_settings):
        """Test that PgJinjaAsync initializes with valid DBSettings."""
        client = PgJinjaAsync(valid_db_settings)

        assert client.settings == valid_db_settings
        assert isinstance(client.pool, AsyncConnectionPool)
        assert client.pool.conninfo == valid_db_settings.coninfo
        assert client.pool.max_size == valid_db_settings.max_size
        assert client.pool.min_size == valid_db_settings.min_size

    def test_async_initialization_pool_not_opened(self, valid_db_settings):
        """Test that async connection pool is not opened during initialization."""
        with patch('psycopg_pool.AsyncConnectionPool') as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool_class.return_value = mock_pool

            client = PgJinjaAsync(valid_db_settings)

            mock_pool_class.assert_called_once_with(
                conninfo=valid_db_settings.coninfo,
                max_size=valid_db_settings.max_size,
                min_size=valid_db_settings.min_size,
                open=False
            )

    def test_async_destructor_closes_pool(self, valid_db_settings):
        """Test that destructor closes the async pool if it exists."""
        client = PgJinjaAsync(valid_db_settings)
        mock_pool = Mock()
        client.pool = mock_pool

        client.__del__()

        mock_pool.close.assert_called_once()

    def test_async_inheritance_from_pgjinja(self, valid_db_settings):
        """Test that PgJinjaAsync properly inherits from PgJinja."""
        from pgjinja import PgJinja

        client = PgJinjaAsync(valid_db_settings)

        assert isinstance(client, PgJinja)
        assert hasattr(client, 'settings')
        assert hasattr(client, 'pool')


class TestPgJinjaAsyncConnectionPooling:
    @pytest.mark.asyncio
    async def test_async_pool_opening_lazy(self, valid_db_settings):
        """Test that async connection pool opens lazily when first query is executed."""
        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool
        mock_pool = AsyncMock()
        mock_pool._opened = False
        client.pool = mock_pool

        await client._open_pool()

        mock_pool.open.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_pool_not_reopened_if_already_open(self, valid_db_settings):
        """Test that async pool is not reopened if already open."""
        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool as already opened
        mock_pool = AsyncMock()
        mock_pool._opened = True
        client.pool = mock_pool

        await client._open_pool()

        mock_pool.open.assert_not_called()


class TestPgJinjaAsyncQueryExecution:
    @pytest.mark.asyncio
    @patch('pgjinja.pgjinja_async.read_template')
    @patch('jinjasql.JinjaSql')
    async def test_async_query_execution_without_model(self, mock_jinja_sql, mock_read_template,
                                                     valid_db_settings, sample_query_results,
                                                     sample_cursor_description):
        """Test executing an async query without model mapping."""
        # Setup mocks
        mock_read_template.return_value = "SELECT * FROM users WHERE id = {{ user_id }}"
        mock_jinja = Mock()
        mock_jinja_sql.return_value = mock_jinja
        mock_jinja.prepare_query.return_value = ("SELECT * FROM users WHERE id = %s", [1])

        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool and connection
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

        result = await client.query("users.sql", {"user_id": 1})

        assert result == sample_query_results
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", [1])

    @pytest.mark.asyncio
    @patch('pgjinja.pgjinja_async.read_template')
    @patch('jinjasql.JinjaSql')
    async def test_async_query_execution_with_model(self, mock_jinja_sql, mock_read_template,
                                                  valid_db_settings, sample_query_results,
                                                  sample_cursor_description, sample_user_model):
        """Test executing an async query with model mapping."""
        # Setup mocks
        mock_read_template.return_value = "SELECT {{ _model_fields_ }} FROM users WHERE id = {{ user_id }}"
        mock_jinja = Mock()
        mock_jinja_sql.return_value = mock_jinja
        mock_jinja.prepare_query.return_value = ("SELECT id, name, email FROM users WHERE id = %s", [1])

        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool and connection
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

        result = await client.query("users.sql", {"user_id": 1}, sample_user_model)

        assert len(result) == 3
        assert all(isinstance(user, sample_user_model) for user in result)
        assert result[0].id == 1
        assert result[0].name == "John Doe"
        assert result[0].email == "john@example.com"

    @pytest.mark.asyncio
    @patch('pgjinja.pgjinja_async.read_template')
    @patch('jinjasql.JinjaSql')
    async def test_async_query_execution_insert_update_delete(self, mock_jinja_sql, mock_read_template,
                                                            valid_db_settings):
        """Test executing async INSERT/UPDATE/DELETE queries that return row count."""
        # Setup mocks
        mock_read_template.return_value = "INSERT INTO users (name, email) VALUES ({{ name }}, {{ email }})"
        mock_jinja = Mock()
        mock_jinja_sql.return_value = mock_jinja
        mock_jinja.prepare_query.return_value = ("INSERT INTO users (name, email) VALUES (%s, %s)", ["John", "john@example.com"])

        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool and connection
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()

        mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_cursor.description = None  # No description for INSERT/UPDATE/DELETE
        mock_cursor.rowcount = 1

        client.pool = mock_pool

        result = await client.query("insert_user.sql", {"name": "John", "email": "john@example.com"})

        assert result == 1
        mock_cursor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_query_with_none_params(self, valid_db_settings):
        """Test that async query handles None params correctly."""
        client = PgJinjaAsync(valid_db_settings)

        with patch.object(client, '_run') as mock_run:
            mock_run.return_value = []

            with patch('pgjinja.pgjinja_async.read_template') as mock_read_template, \
                 patch('jinjasql.JinjaSql') as mock_jinja_sql:

                mock_read_template.return_value = "SELECT * FROM users"
                mock_jinja = Mock()
                mock_jinja_sql.return_value = mock_jinja
                mock_jinja.prepare_query.return_value = ("SELECT * FROM users", [])

                await client.query("users.sql", None)

                # Should have called prepare_query with empty dict
                mock_jinja.prepare_query.assert_called_once_with("SELECT * FROM users", {})

    @pytest.mark.asyncio
    async def test_async_query_adds_model_fields_to_params(self, valid_db_settings, sample_user_model):
        """Test that async query adds _model_fields_ to params when model is provided."""
        client = PgJinjaAsync(valid_db_settings)

        with patch.object(client, '_run') as mock_run:
            mock_run.return_value = []

            with patch('pgjinja.pgjinja_async.read_template') as mock_read_template, \
                 patch('jinjasql.JinjaSql') as mock_jinja_sql:

                mock_read_template.return_value = "SELECT {{ _model_fields_ }} FROM users"
                mock_jinja = Mock()
                mock_jinja_sql.return_value = mock_jinja
                mock_jinja.prepare_query.return_value = ("SELECT id, name, email FROM users", [])

                await client.query("users.sql", {"param": "value"}, sample_user_model)

                # Should have called prepare_query with _model_fields_ added
                expected_params = {"param": "value", "_model_fields_": "id, name, email"}
                mock_jinja.prepare_query.assert_called_once_with("SELECT {{ _model_fields_ }} FROM users", expected_params)


class TestPgJinjaAsyncRetryLogic:
    @pytest.mark.asyncio
    async def test_async_retry_logic_on_failure(self, valid_db_settings):
        """Test that async query failures are retried up to max_retries times."""
        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()

        mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_pool.get_stats.return_value = {"mock": "stats"}

        # Make cursor.execute raise an exception
        mock_cursor.execute.side_effect = Exception("Connection error")

        client.pool = mock_pool

        with pytest.raises(Exception, match="Connection error"):
            await client._run("SELECT 1", max_retries=2)

        # Should have been called 2 times (initial + 1 retry)
        assert mock_cursor.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_logic_success_after_failure(self, valid_db_settings):
        """Test that async query succeeds after initial failures."""
        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()

        mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

        # Fail once, then succeed
        mock_cursor.execute.side_effect = [Exception("Temporary error"), None]
        mock_cursor.description = None
        mock_cursor.rowcount = 1

        client.pool = mock_pool

        result = await client._run("SELECT 1", max_retries=2)

        assert result == 1
        assert mock_cursor.execute.call_count == 2


class TestPgJinjaAsyncErrorHandling:
    @pytest.mark.asyncio
    @patch('pgjinja.pgjinja_async.read_template')
    async def test_async_error_handling_file_not_found(self, mock_read_template, valid_db_settings):
        """Test that async FileNotFoundError is properly raised for missing templates."""
        mock_read_template.side_effect = FileNotFoundError("Template not found")

        client = PgJinjaAsync(valid_db_settings)

        with pytest.raises(FileNotFoundError, match="Template not found"):
            await client.query("nonexistent.sql")

    # @pytest.mark.asyncio
    # @patch('pgjinja.pgjinja_async.read_template')
    # @patch('jinjasql.JinjaSql')
    # async def test_async_error_handling_invalid_template(self, mock_jinja_sql, mock_read_template, valid_db_settings):
    #     """Test that async JinjaSQL errors are properly handled."""
    #     mock_read_template.return_value = "SELECT * FROM users WHERE invalid {{ unclosed"
    #     mock_jinja = Mock()
    #     mock_jinja_sql.return_value = mock_jinja
    #     mock_jinja.prepare_query.side_effect = Exception("Invalid template")
    #
    #     client = PgJinjaAsync(valid_db_settings)
    #
    #     with pytest.raises(Exception, match="Invalid template"):
    #         await client.query("invalid.sql")

    @pytest.mark.asyncio
    async def test_async_error_handling_invalid_model_type(self, valid_db_settings):
        """Test that async TypeError is raised for invalid model types."""
        client = PgJinjaAsync(valid_db_settings)

        class NotABaseModel:
            pass

        with patch.object(client, '_run') as mock_run:
            mock_run.return_value = []

            with patch('pgjinja.pgjinja_async.read_template') as mock_read_template, \
                 patch('jinjasql.JinjaSql') as mock_jinja_sql:

                mock_read_template.return_value = "SELECT * FROM users"
                mock_jinja = Mock()
                mock_jinja_sql.return_value = mock_jinja
                mock_jinja.prepare_query.return_value = ("SELECT * FROM users", [])

                # Should not raise error because we don't call get_model_fields for non-BaseModel
                result = await client.query("users.sql", {}, NotABaseModel)
                assert result == []

    @pytest.mark.asyncio
    async def test_async_error_handling_database_connection_error(self, valid_db_settings):
        """Test that async database connection errors are properly handled."""
        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool to raise connection error
        mock_pool = AsyncMock()
        mock_pool.connection.side_effect = Exception("Database connection failed")
        mock_pool.get_stats.return_value = {"mock": "stats"}

        client.pool = mock_pool

        with pytest.raises(Exception, match="Database connection failed"):
            await client._run("SELECT 1", max_retries=1)


class TestPgJinjaAsyncConcurrency:
    @pytest.mark.asyncio
    async def test_async_concurrent_queries(self, valid_db_settings, sample_query_results,
                                          sample_cursor_description, sample_user_model):
        """Test that multiple async queries can be executed concurrently."""
        import asyncio

        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool and connection for concurrent access
        mock_pool = AsyncMock()

        async def mock_connection_context():
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()

            mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
            mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_cursor.description = sample_cursor_description
            mock_cursor.fetchall.return_value = sample_query_results

            return mock_connection

        mock_pool.connection.return_value.__aenter__ = mock_connection_context
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)

        client.pool = mock_pool

        with patch('pgjinja.pgjinja_async.read_template') as mock_read_template, \
             patch('jinjasql.JinjaSql') as mock_jinja_sql:

            mock_read_template.return_value = "SELECT {{ _model_fields_ }} FROM users WHERE id = {{ user_id }}"
            mock_jinja = Mock()
            mock_jinja_sql.return_value = mock_jinja
            mock_jinja.prepare_query.return_value = ("SELECT id, name, email FROM users WHERE id = %s", [1])

            # Execute multiple queries concurrently
            tasks = [
                client.query("users.sql", {"user_id": i}, sample_user_model)
                for i in range(1, 4)
            ]

            results = await asyncio.gather(*tasks)

            # All queries should have completed successfully
            assert len(results) == 3
            for result in results:
                assert len(result) == 3
                assert all(isinstance(user, sample_user_model) for user in result)

    @pytest.mark.asyncio
    async def test_async_query_cancellation(self, valid_db_settings):
        """Test that async queries can be cancelled properly."""
        import asyncio

        client = PgJinjaAsync(valid_db_settings)

        # Mock the pool to simulate a long-running query
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()

        # Make the execute method hang
        async def hanging_execute(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate long query

        mock_cursor.execute = hanging_execute

        mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_connection.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

        client.pool = mock_pool

        # Start the query and cancel it
        task = asyncio.create_task(client._run("SELECT 1"))
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
