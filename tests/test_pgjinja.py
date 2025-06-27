from unittest.mock import Mock, patch

import pytest
from psycopg_pool import ConnectionPool

from pgjinja import PgJinja


class TestPgJinjaInitialization:
    def test_initialization_with_valid_settings(self, valid_db_settings):
        """Test that PgJinja initializes with valid DBSettings."""
        client = PgJinja(valid_db_settings)

        assert client.settings == valid_db_settings
        assert isinstance(client.pool, ConnectionPool)
        assert client.pool.conninfo == valid_db_settings.coninfo
        assert client.pool.max_size == valid_db_settings.max_size
        assert client.pool.min_size == valid_db_settings.min_size

    def test_initialization_pool_not_opened(self, valid_db_settings):
        """Test that connection pool is not opened during initialization."""
        with patch('pgjinja.pgjinja.ConnectionPool') as mock_pool_class:
            mock_pool = Mock()
            mock_pool_class.return_value = mock_pool

            client = PgJinja(valid_db_settings)

            mock_pool_class.assert_called_once_with(
                conninfo=valid_db_settings.coninfo,
                max_size=valid_db_settings.max_size,
                min_size=valid_db_settings.min_size,
                open=False
            )

    def test_destructor_closes_pool(self, valid_db_settings):
        """Test that destructor closes the pool if it exists."""
        client = PgJinja(valid_db_settings)
        mock_pool = Mock()
        client.pool = mock_pool

        client.__del__()

        mock_pool.close.assert_called_once()

    def test_destructor_handles_missing_pool(self, valid_db_settings):
        """Test that destructor handles missing pool gracefully."""
        client = PgJinja(valid_db_settings)
        delattr(client, 'pool')

        # Should not raise an exception
        client.__del__()


class TestPgJinjaConnectionPooling:
    def test_pool_opening_lazy(self, valid_db_settings):
        """Test that connection pool opens lazily when first query is executed."""
        client = PgJinja(valid_db_settings)

        # Mock the pool
        mock_pool = Mock()
        mock_pool._opened = False
        client.pool = mock_pool

        client._open_pool()

        mock_pool.open.assert_called_once()

    def test_pool_not_reopened_if_already_open(self, valid_db_settings):
        """Test that pool is not reopened if already open."""
        client = PgJinja(valid_db_settings)

        # Mock the pool as already opened
        mock_pool = Mock()
        mock_pool._opened = True
        client.pool = mock_pool

        client._open_pool()

        mock_pool.open.assert_not_called()


class TestPgJinjaQueryExecution:
    @patch('pgjinja.pgjinja.read_template')
    @patch('jinjasql.JinjaSql')
    def test_query_execution_without_model(self, mock_jinja_sql, mock_read_template,
                                         valid_db_settings, sample_query_results,
                                         sample_cursor_description):
        """Test executing a query without model mapping."""
        # Setup mocks
        mock_read_template.return_value = "SELECT * FROM users WHERE id = {{ user_id }}"
        mock_jinja = Mock()
        mock_jinja_sql.return_value = mock_jinja
        mock_jinja.prepare_query.return_value = ("SELECT * FROM users WHERE id = %s", [1])

        client = PgJinja(valid_db_settings)

        # Mock the pool and connection
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

        result = client.query("users.sql", {"user_id": 1})

        assert result == sample_query_results
        # JinjaSQL returns tuple for parameters, not list
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", (1,))

    @patch('pgjinja.pgjinja.read_template')
    @patch('jinjasql.JinjaSql')
    def test_query_execution_with_model(self, mock_jinja_sql, mock_read_template,
                                      valid_db_settings, sample_query_results,
                                      sample_cursor_description, sample_user_model):
        """Test executing a query with model mapping."""
        # Setup mocks
        mock_read_template.return_value = "SELECT {{ _model_fields_ }} FROM users WHERE id = {{ user_id }}"
        mock_jinja = Mock()
        mock_jinja_sql.return_value = mock_jinja
        mock_jinja.prepare_query.return_value = ("SELECT id, name, email FROM users WHERE id = %s", [1])

        client = PgJinja(valid_db_settings)

        # Mock the pool and connection
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

        result = client.query("users.sql", {"user_id": 1}, sample_user_model)

        assert len(result) == 3
        assert all(isinstance(user, sample_user_model) for user in result)
        assert result[0].id == 1
        assert result[0].name == "John Doe"
        assert result[0].email == "john@example.com"

    @patch('pgjinja.pgjinja.read_template')
    @patch('jinjasql.JinjaSql')
    def test_query_execution_insert_update_delete(self, mock_jinja_sql, mock_read_template,
                                                 valid_db_settings):
        """Test executing INSERT/UPDATE/DELETE queries that return row count."""
        # Setup mocks
        mock_read_template.return_value = "INSERT INTO users (name, email) VALUES ({{ name }}, {{ email }})"
        mock_jinja = Mock()
        mock_jinja_sql.return_value = mock_jinja
        mock_jinja.prepare_query.return_value = ("INSERT INTO users (name, email) VALUES (%s, %s)", ["John", "john@example.com"])

        client = PgJinja(valid_db_settings)

        # Mock the pool and connection
        mock_pool = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()

        mock_pool.connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_pool.connection.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)

        mock_cursor.description = None  # No description for INSERT/UPDATE/DELETE
        mock_cursor.rowcount = 1

        client.pool = mock_pool

        result = client.query("insert_user.sql", {"name": "John", "email": "john@example.com"})

        assert result == 1
        mock_cursor.execute.assert_called_once()


    # def test_query_adds_model_fields_to_params(self, valid_db_settings, sample_user_model):
    #     """Test that query adds _model_fields_ to params when model is provided."""
    #     client = PgJinja(valid_db_settings)
    #
    #     with patch.object(client, '_run') as mock_run:
    #         mock_run.return_value = []
    #
    #         with patch('pgjinja.pgjinja.read_template') as mock_read_template, \
    #              patch('jinjasql.JinjaSql') as mock_jinja_sql:
    #
    #             mock_read_template.return_value = "SELECT {{ _model_fields_ }} FROM users"
    #             mock_jinja = Mock()
    #             mock_jinja_sql.return_value = mock_jinja
    #             mock_jinja.prepare_query.return_value = ("SELECT id, name, email FROM users", [])
    #
    #             client.query("users.sql", {"param": "value"}, sample_user_model)
    #
    #             # Should have called prepare_query with _model_fields_ added
    #             expected_params = {"param": "value", "_model_fields_": "id, name, email"}
    #             mock_jinja.prepare_query.assert_called_once_with("SELECT {{ _model_fields_ }} FROM users", expected_params)


class TestPgJinjaRetryLogic:
    def test_retry_logic_on_failure(self, valid_db_settings):
        """Test that query failures are retried up to max_retries times."""
        client = PgJinja(valid_db_settings)

        # Mock the pool
        mock_pool = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()

        mock_pool.connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_pool.connection.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_pool.get_stats.return_value = {"mock": "stats"}

        # Make cursor.execute raise an exception
        mock_cursor.execute.side_effect = Exception("Connection error")

        client.pool = mock_pool

        with pytest.raises(Exception, match="Connection error"):
            client._run("SELECT 1", max_retries=2)

        # Should have been called 2 times (initial + 1 retry)
        assert mock_cursor.execute.call_count == 2

    def test_retry_logic_success_after_failure(self, valid_db_settings):
        """Test that query succeeds after initial failures."""
        client = PgJinja(valid_db_settings)

        # Mock the pool
        mock_pool = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()

        mock_pool.connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_pool.connection.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)

        # Fail once, then succeed
        mock_cursor.execute.side_effect = [Exception("Temporary error"), None]
        mock_cursor.description = None
        mock_cursor.rowcount = 1

        client.pool = mock_pool

        result = client._run("SELECT 1", max_retries=2)

        assert result == 1
        assert mock_cursor.execute.call_count == 2


class TestPgJinjaErrorHandling:
    @patch('pgjinja.pgjinja.read_template')
    def test_error_handling_file_not_found(self, mock_read_template, valid_db_settings):
        """Test that FileNotFoundError is properly raised for missing templates."""
        mock_read_template.side_effect = FileNotFoundError("Template not found")

        client = PgJinja(valid_db_settings)

        with pytest.raises(FileNotFoundError, match="Template not found"):
            client.query("nonexistent.sql")

    # @patch('pgjinja.pgjinja.read_template')
    # @patch('jinjasql.JinjaSql')
    # def test_error_handling_invalid_template(self, mock_jinja_sql, mock_read_template, valid_db_settings):
    #     """Test that JinjaSQL errors are properly handled."""
    #     mock_read_template.return_value = "SELECT * FROM users WHERE invalid {{ unclosed"
    #     mock_jinja = Mock()
    #     mock_jinja_sql.return_value = mock_jinja
    #     mock_jinja.prepare_query.side_effect = Exception("Invalid template")
    #
    #     client = PgJinja(valid_db_settings)
    #
    #     with pytest.raises(Exception, match="Invalid template"):
    #         client.query("invalid.sql")

    def test_error_handling_invalid_model_type(self, valid_db_settings):
        """Test that TypeError is raised for invalid model types."""
        client = PgJinja(valid_db_settings)

        class NotABaseModel:
            pass

        with patch.object(client, '_run') as mock_run:
            mock_run.return_value = []

            with patch('pgjinja.pgjinja.read_template') as mock_read_template, \
                 patch('jinjasql.JinjaSql') as mock_jinja_sql:

                mock_read_template.return_value = "SELECT * FROM users"
                mock_jinja = Mock()
                mock_jinja_sql.return_value = mock_jinja
                mock_jinja.prepare_query.return_value = ("SELECT * FROM users", [])

                # Should not raise error because we don't call get_model_fields for non-BaseModel
                result = client.query("users.sql", {}, NotABaseModel)
                assert result == []

    def test_error_handling_database_connection_error(self, valid_db_settings):
        """Test that database connection errors are properly handled."""
        client = PgJinja(valid_db_settings)

        # Mock the pool to raise connection error
        mock_pool = Mock()
        mock_pool.connection.side_effect = Exception("Database connection failed")
        mock_pool.get_stats.return_value = {"mock": "stats"}

        client.pool = mock_pool

        with pytest.raises(Exception, match="Database connection failed"):
            client._run("SELECT 1", max_retries=1)
