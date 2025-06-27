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
