from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel

from pgjinja import PgJinja


class TestPgJinjaBasicFunctionality:
    """Basic functionality tests for PgJinja without complex mocking."""

    def test_initialization_basic(self, valid_db_settings):
        """Test basic initialization of PgJinja."""
        client = PgJinja(valid_db_settings)

        assert client.settings == valid_db_settings
        assert hasattr(client, 'pool')

    def test_pool_opening_mechanism(self, valid_db_settings):
        """Test pool opening mechanism."""
        client = PgJinja(valid_db_settings)

        # Mock the pool
        mock_pool = Mock()
        mock_pool._opened = False
        client.pool = mock_pool

        client._open_pool()

        mock_pool.open.assert_called_once()

    def test_model_fields_integration(self, valid_db_settings):
        """Test model fields integration with parameters."""
        class TestModel(BaseModel):
            id: int
            name: str
            email: str

        client = PgJinja(valid_db_settings)

        # Mock _run method to capture parameters
        with patch.object(client, '_run') as mock_run:
            mock_run.return_value = []

            # Mock template reading and JinjaSQL
            with patch('pgjinja.pgjinja.read_template') as mock_read_template, \
                 patch('pgjinja.pgjinja.JinjaSql') as mock_jinja_sql:

                mock_read_template.return_value = "SELECT {{ _model_fields_ }} FROM users"
                mock_jinja = Mock()
                mock_jinja_sql.return_value = mock_jinja
                mock_jinja.prepare_query.return_value = ("SELECT id, name, email FROM users", ())

                # Execute query
                client.query("test.sql", {"param": "value"}, TestModel)

                # Verify JinjaSQL was called with model fields added
                call_args = mock_jinja.prepare_query.call_args[0]
                assert call_args[0] == "SELECT {{ _model_fields_ }} FROM users"

                # Check that _model_fields_ was added to parameters
                params = call_args[1]
                assert "_model_fields_" in params
                assert params["_model_fields_"] == "id, name, email"
                assert params["param"] == "value"

    def test_parameter_handling_none_params(self, valid_db_settings):
        """Test parameter handling when params is None."""
        client = PgJinja(valid_db_settings)

        with patch.object(client, '_run') as mock_run:
            mock_run.return_value = []

            with patch('pgjinja.pgjinja.read_template') as mock_read_template, \
                 patch('pgjinja.pgjinja.JinjaSql') as mock_jinja_sql:

                mock_read_template.return_value = "SELECT * FROM users"
                mock_jinja = Mock()
                mock_jinja_sql.return_value = mock_jinja
                mock_jinja.prepare_query.return_value = ("SELECT * FROM users", ())

                # Execute with None params
                client.query("test.sql", None)

                # Verify prepare_query was called with empty dict
                call_args = mock_jinja.prepare_query.call_args[0]
                assert call_args[1] == {}

    def test_retry_logic_basic(self, valid_db_settings):
        """Test basic retry logic functionality."""
        client = PgJinja(valid_db_settings)

        # Mock pool and connections
        mock_pool = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()

        # Setup context managers
        mock_pool.connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_pool.connection.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)

        # Mock stats for error logging
        mock_pool.get_stats.return_value = {"test": "stats"}

        # Make execute fail twice, then succeed
        mock_cursor.execute.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            None  # Success on third try
        ]
        mock_cursor.description = None
        mock_cursor.rowcount = 1

        client.pool = mock_pool

        # Should succeed after retries
        result = client._run("SELECT 1", max_retries=3)

        assert result == 1
        assert mock_cursor.execute.call_count == 3

    def test_error_propagation(self, valid_db_settings):
        """Test that errors are properly propagated."""
        client = PgJinja(valid_db_settings)

        # Test file not found error
        with patch('pgjinja.pgjinja.read_template') as mock_read_template:
            mock_read_template.side_effect = FileNotFoundError("Template not found")

            with pytest.raises(FileNotFoundError, match="Template not found"):
                client.query("nonexistent.sql")

    def test_destructor_cleanup(self, valid_db_settings):
        """Test destructor properly cleans up resources."""
        client = PgJinja(valid_db_settings)

        # Mock pool
        mock_pool = Mock()
        client.pool = mock_pool

        # Call destructor
        client.__del__()

        # Verify pool was closed
        mock_pool.close.assert_called_once()

    def test_query_result_mapping_basic(self, valid_db_settings):
        """Test basic query result mapping to models."""
        class User(BaseModel):
            id: int
            name: str
            email: str

        client = PgJinja(valid_db_settings)

        # Mock the execution pipeline
        with patch.object(client, '_run') as mock_run:
            # Simulate database results
            mock_run.return_value = [
                User(id=1, name="John", email="john@example.com"),
                User(id=2, name="Jane", email="jane@example.com")
            ]

            with patch('pgjinja.pgjinja.read_template') as mock_read_template, \
                 patch('pgjinja.pgjinja.JinjaSql') as mock_jinja_sql:

                mock_read_template.return_value = "SELECT * FROM users"
                mock_jinja = Mock()
                mock_jinja_sql.return_value = mock_jinja
                mock_jinja.prepare_query.return_value = ("SELECT * FROM users", ())

                result = client.query("users.sql", {}, User)

                assert len(result) == 2
                assert all(isinstance(user, User) for user in result)
                assert result[0].name == "John"
                assert result[1].name == "Jane"
