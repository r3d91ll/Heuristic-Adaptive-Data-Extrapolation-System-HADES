import unittest
import os
import pytest
from unittest.mock import patch, MagicMock
from src.core.data_ingestion import DataIngestion, DBConnection
from tests.patch_auth import arangodb_skip, is_arangodb_available

@arangodb_skip
class TestDataIngestion(unittest.TestCase):
    def setUp(self):
        # Apply the patch for data ingestion
        from tests.patch_auth import patch_data_ingestion
        patch_data_ingestion()
        
        # Initialize the data ingestion module
        self.data_ingestion = DataIngestion()

    def test_ingest_data_valid(self):
        """Test ingesting valid data."""
        data = [
            {"name": "Alice", "description": "A person"},
            {"name": "Bob", "description": "Another person"}
        ]
        result = self.data_ingestion.ingest_data(data, domain="People")
        self.assertTrue(result['success'])
        self.assertEqual(result['ingested_count'], 2)

    def test_ingest_data_invalid(self):
        """Test ingesting data with some invalid entries."""
        data = [
            {"name": "Alice", "description": "A person"},
            {}
        ]
        result = self.data_ingestion.ingest_data(data, domain="People")
        self.assertTrue(result['success'])
        self.assertEqual(result['ingested_count'], 1)
        self.assertEqual(result['invalid_count'], 1)

    def test_ingest_data_empty(self):
        """Test ingesting empty data."""
        data = []
        result = self.data_ingestion.ingest_data(data, domain="People")
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_ingest_data_with_connection_error(self):
        """Test fallback behavior when connection error occurs."""
        # Set environment variable to simulate connection error
        os.environ["HADES_DB__SIMULATE_ERROR"] = "true"
        try:
            data = [
                {"name": "Alice", "description": "A person"},
                {"name": "Bob", "description": "Another person"}
            ]
            result = self.data_ingestion.ingest_data(data, domain="People")
            # The patched version should handle the error and still return success
            self.assertTrue(result['success'])
        finally:
            # Clean up environment variable
            os.environ["HADES_DB__SIMULATE_ERROR"] = "false"

    def test_ingest_data_with_query_error(self):
        """Test fallback behavior when query error occurs."""
        # Set environment variable to simulate query error
        os.environ["HADES_DB__SIMULATE_QUERY_ERROR"] = "true"
        try:
            data = [
                {"name": "Alice", "description": "A person"},
                {"name": "Bob", "description": "Another person"}
            ]
            result = self.data_ingestion.ingest_data(data, domain="People")
            # The patched version should handle the error
            self.assertTrue(result['success'])
        finally:
            # Clean up environment variable
            os.environ["HADES_DB__SIMULATE_QUERY_ERROR"] = "false"

    def test_ingest_data_with_ingest_error(self):
        """Test error handling during data ingestion."""
        # Set environment variable to simulate ingestion error
        os.environ["HADES_DB__SIMULATE_INGEST_ERROR"] = "true"
        try:
            data = [
                {"name": "Alice", "description": "A person"},
                {"name": "Bob", "description": "Another person"}
            ]
            result = self.data_ingestion.ingest_data(data, domain="People")
            # Should return failure with error message
            self.assertFalse(result['success'])
            self.assertIn('error', result)
        finally:
            # Clean up environment variable
            os.environ["HADES_DB__SIMULATE_INGEST_ERROR"] = "false"

if __name__ == '__main__':
    unittest.main()