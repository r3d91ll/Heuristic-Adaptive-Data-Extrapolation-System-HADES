import unittest
from src.db.connection import DBConnection

class TestDBConnection(unittest.TestCase):
    def setUp(self):
        self.db_connection = DBConnection()

    def test_connect_success(self):
        result = self.db_connection.connect()
        self.assertTrue(result)

    def test_execute_query_success(self):
        query = "FOR doc IN entities RETURN doc"
        result = self.db_connection.execute_query(query)
        self.assertTrue(result['success'])
        self.assertIn('result', result)

if __name__ == '__main__':
    unittest.main()
