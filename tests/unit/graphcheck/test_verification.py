import unittest
from src.graphcheck.verification import GraphCheck

class TestGraphCheck(unittest.TestCase):
    def setUp(self):
        self.graph_check = GraphCheck()

    def test_verify_claims(self):
        claims = [
            {"text": "Alice knows Bob"},
            {"text": "Bob works at Company"}
        ]
        result = self.graph_check.verify_claims(claims)
        self.assertTrue(result['success'])
        self.assertIn('verified_count', result)

if __name__ == '__main__':
    unittest.main()