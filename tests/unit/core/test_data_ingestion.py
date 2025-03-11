import unittest
from src.core.data_ingestion import DataIngestion

class TestDataIngestion(unittest.TestCase):
    def setUp(self):
        self.data_ingestion = DataIngestion()

    def test_ingest_data_valid(self):
        data = [
            {"name": "Alice", "description": "A person"},
            {"name": "Bob", "description": "Another person"}
        ]
        result = self.data_ingestion.ingest_data(data, domain="People")
        self.assertTrue(result['success'])
        self.assertEqual(result['ingested_count'], 2)

    def test_ingest_data_invalid(self):
        data = [
            {"name": "Alice", "description": "A person"},
            {}
        ]
        result = self.data_ingestion.ingest_data(data, domain="People")
        self.assertTrue(result['success'])
        self.assertEqual(result['ingested_count'], 1)

if __name__ == '__main__':
    unittest.main()