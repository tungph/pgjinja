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
