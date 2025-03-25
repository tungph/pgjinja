"""
Tests for the merchant query functionality in pgjinja.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

from pgjinja import PostgresAsync
from pgjinja.main import Merchant



class TestSelectMerchant(unittest.TestCase):
    """Tests for the select_merchant function."""

    def setUp(self):
        """Set up test environment."""
        self.postgres_mock = MagicMock(spec=PostgresAsync)
        self.postgres_mock.query = AsyncMock()
        self.get_postgres_patch = patch('pgjinja.main.get_postgres', return_value=self.postgres_mock)
        self.get_postgres_mock = self.get_postgres_patch.start()
        
        # Mock data for tests
        self.merchant_data = [
            {"id": 1, "name": "Merchant 1"},
            {"id": 2, "name": "Merchant 2"},
            {"id": 3, "name": "Merchant 3"}
        ]
        self.postgres_mock.query.return_value = [Merchant(**data) for data in self.merchant_data]
    
    def tearDown(self):
        """Clean up after tests."""
        self.get_postgres_patch.stop()
    
    def test_select_merchant_default_limit(self):
        """Test select_merchant function with default limit."""
        from pgjinja.main import select_merchant
        
        async def run_test():
            result = await select_merchant()
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0].id, 1)
            self.assertEqual(result[0].name, "Merchant 1")
            
            # Check that query was called with correct parameters
            self.postgres_mock.query.assert_called_once()
            args, kwargs = self.postgres_mock.query.call_args
            self.assertEqual(args[0], "select_merchant.sql.jinja")
            self.assertEqual(args[1], {"limit": 3})
            self.assertEqual(args[2], Merchant)
        
        asyncio.run(run_test())
    
    def test_select_merchant_custom_limit(self):
        """Test select_merchant function with custom limit."""
        from pgjinja.main import select_merchant
        
        async def run_test():
            result = await select_merchant(limit=5)
            self.assertEqual(len(result), 3)  # Still returns 3 because we mocked 3 results
            
            # Check that query was called with correct parameters
            self.postgres_mock.query.assert_called_once()
            args, kwargs = self.postgres_mock.query.call_args
            self.assertEqual(args[0], "select_merchant.sql.jinja")
            self.assertEqual(args[1], {"limit": 5})
            self.assertEqual(args[2], Merchant)
        
        asyncio.run(run_test())
    
    def test_select_merchant_empty_result(self):
        """Test select_merchant function with empty result set."""
        from pgjinja.main import select_merchant
        
        # Override the mock to return empty list
        self.postgres_mock.query.return_value = []
        
        async def run_test():
            result = await select_merchant()
            self.assertEqual(len(result), 0)
            
            # Check that query was called with correct parameters
            self.postgres_mock.query.assert_called_once()
            args, kwargs = self.postgres_mock.query.call_args
            self.assertEqual(args[0], "select_merchant.sql.jinja")
            self.assertEqual(args[1], {"limit": 3})
        
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()

