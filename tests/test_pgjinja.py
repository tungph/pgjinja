import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel, Field

from pgjinja import PgJinja


class TestPgJinja(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create temp directory and template
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.sql")
        with open(self.test_file, "w") as f:
            f.write("""
                SELECT *
                FROM users
                {% if user_id %}
                WHERE id = {{ user_id }}
                {% endif %}
            """)

        # Create cursor mock with async context support
        self.cursor = MagicMock()
        self.cursor.description = [("id",), ("name",)]
        self.cursor.fetchall = AsyncMock(return_value=[(1, "test")])
        self.cursor.execute = AsyncMock()

        # Create connection mock with async context support
        self.conn = MagicMock()
        self.conn.cursor = MagicMock(return_value=self.cursor)

        # Setup async context managers
        self.cursor.__aenter__ = AsyncMock(return_value=self.cursor)
        self.cursor.__aexit__ = AsyncMock(return_value=None)
        self.conn.__aenter__ = AsyncMock(return_value=self.conn)
        self.conn.__aexit__ = AsyncMock(return_value=None)

        # Create pool mock
        # Create pool mock
        self.pool = MagicMock()
        self.pool.connection = MagicMock(return_value=self.conn)
        self.pool.open = AsyncMock()
        # Set _opened to False initially to match implementation
        self.pool._opened = False
        # Setup pool patcher
        self.pool_patcher = patch("pgjinja.pgjinja.AsyncConnectionPool")
        self.mock_pool_class = self.pool_patcher.start()
        self.mock_pool_class.return_value = self.pool

        # Create PostgresAsync instance
        self.db_client = PgJinja(
            user="test_user",
            password="test_password",
            host="localhost",
            port=5432,
            dbname="test_db",
            template_dir=self.temp_dir,
        )

    async def asyncTearDown(self):
        self.pool_patcher.stop()
        os.unlink(self.test_file)
        os.rmdir(self.temp_dir)

    def test_initialization(self):
        """Test basic initialization"""
        self.assertEqual(self.db_client.db, "localhost:5432/test_db")
        self.assertEqual(str(self.db_client.template_dir), self.temp_dir)
        self.assertIsInstance(self.db_client.template_dir, Path)
        self.assertEqual(self.db_client.pool._opened, False)

    async def test_connection_management(self):
        """Test connection pool management"""
        # Initially pool is not opened
        self.assertFalse(self.db_client.pool._opened)

        # Test that _open_pool calls self.pool.open
        await self.db_client._open_pool()
        self.pool.open.assert_called_once()

        # After _open_pool, the pool should be marked as opened
        self.pool._opened = True
        self.assertTrue(self.db_client.pool._opened)

        await self.db_client._open_pool()
        self.assertEqual(self.pool.open.call_count, 1)

    async def test_basic_query(self):
        """Test simple query execution"""
        result = await self.db_client._run("SELECT * FROM test")
        self.cursor.execute.assert_called_once_with("SELECT * FROM test", ())
        self.assertEqual(result, [(1, "test")])

    async def test_parameterized_query(self):
        """Test query with parameters"""
        result = await self.db_client._run("SELECT * FROM test WHERE id = %s", (1,))
        self.cursor.execute.assert_called_once_with(
            "SELECT * FROM test WHERE id = %s", (1,)
        )
        self.assertEqual(result, [(1, "test")])

    async def test_model_mapping(self):
        """Test query with model mapping using Pydantic BaseModel"""

        class TestModel(BaseModel):
            id: int
            name: str

        result = await self.db_client._run("SELECT * FROM test", model=TestModel)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TestModel)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].name, "test")

    async def test_template_query(self):
        """Test query from template file"""
        result = await self.db_client.query("test.sql", {"user_id": 1})
        executed_query = self.cursor.execute.call_args[0][0].strip()
        self.assertIn("WHERE id = %s", executed_query)
        params = self.cursor.execute.call_args[0][1]
        self.assertEqual(params, (1,))
        self.assertEqual(result, [(1, "test")])

    async def test_update_query(self):
        """Test non-select query"""
        self.cursor.description = None
        self.cursor.rowcount = 1

        result = await self.db_client._run("UPDATE test SET value = %s", (42,))
        self.cursor.execute.assert_called_once_with("UPDATE test SET value = %s", (42,))
        self.assertEqual(result, 1)

    async def test_error_handling(self):
        """Test database error handling"""
        self.cursor.execute.side_effect = Exception("Database error")

        with self.assertRaises(Exception) as context:
            await self.db_client._run("SELECT * FROM missing_table")
        self.assertEqual(str(context.exception), "Database error")

    async def test_missing_template(self):
        """Test handling of missing template files"""
        with self.assertRaises(FileNotFoundError):
            await self.db_client.query("nonexistent.sql", {})

    def test_get_model_fields(self):
        """Test the _get_model_fields function with Pydantic models"""
        from pgjinja.pgjinja import _get_model_fields

        class SimpleModel(BaseModel):
            id: int
            name: str

        fields = _get_model_fields(SimpleModel)
        self.assertEqual(fields, "id, name")

        class ModelWithAlias(BaseModel):
            user_id: int = Field(validation_alias="id")
            user_name: str = Field(validation_alias="name")

        fields = _get_model_fields(ModelWithAlias)
        self.assertEqual(fields, "id, name")

        # Test error case with non-BaseModel class
        class RegularClass:
            def __init__(self, id: int, name: str):
                self.id = id
                self.name = name

        with self.assertRaises(TypeError):
            _get_model_fields(RegularClass)

    async def test_query_with_pydantic_model(self):
        """Test query method with Pydantic model to verify field integration"""
        # Setup custom description and results for this test
        self.cursor.description = [("id",), ("name",), ("email",)]
        self.cursor.fetchall = AsyncMock(return_value=[(1, "test", "test@example.com")])

        class User(BaseModel):
            id: int
            name: str
            email: str

        # Create a mock for _read_text to avoid file operations
        with patch("pgjinja.pgjinja._read_text") as mock_read_text:
            mock_read_text.return_value = "SELECT {{ _model_fields_ }} FROM users"

            result = await self.db_client.query("user.sql", model=User)

            # Verify the model fields were properly injected into the query
            # JinjaSql is using param_style="format", so we expect placeholders (%s)
            self.assertIn("SELECT %s FROM users", self.cursor.execute.call_args[0][0])
            self.assertEqual(len(result), 1)
            self.assertIsInstance(result[0], User)
            self.assertEqual(result[0].id, 1)
            self.assertEqual(result[0].name, "test")
            self.assertEqual(result[0].email, "test@example.com")

    async def test_handle_reconnect_failure(self):
        """Test the reconnection failure handler"""
        from pgjinja.pgjinja import _handle_reconnect_failure

        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()
        mock_pool.open = AsyncMock()

        await _handle_reconnect_failure(mock_pool)

        mock_pool.close.assert_called_once()
        mock_pool.open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
