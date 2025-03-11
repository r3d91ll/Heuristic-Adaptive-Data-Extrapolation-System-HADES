import unittest
from src.rag.path_rag import PathRAG

class TestPathRAG(unittest.TestCase):
    def setUp(self):
        self.path_rag = PathRAG()

    def test_retrieve_paths(self):
        query = "Alice"
        result = self.path_rag.retrieve_paths(query, max_paths=5)
        self.assertTrue(result['success'])
        self.assertIn('paths', result)

if __name__ == '__main__':
    unittest.main()