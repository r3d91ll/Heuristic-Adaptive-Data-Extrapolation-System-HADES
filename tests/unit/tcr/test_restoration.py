import unittest
from src.tcr.restoration import TripleContextRestoration

class TestTripleContextRestoration(unittest.TestCase):
    def setUp(self):
        self.tcr = TripleContextRestoration()

    def test_extract_triples(self):
        path = {
            'nodes': [
                {'subject': 'Alice', 'predicate': 'knows', 'object': 'Bob'},
                {'subject': 'Bob', 'predicate': 'works_at', 'object': 'Company'}
            ]
        }
        triples = self.tcr._extract_triples(path)
        expected_triples = [
            {'subject': 'Alice', 'predicate': 'knows', 'object': 'Bob'},
            {'subject': 'Bob', 'predicate': 'works_at', 'object': 'Company'}
        ]
        self.assertEqual(triples, expected_triples)

    def test_restore_context_for_path(self):
        paths = [
            {
                'nodes': [
                    {'subject': 'Alice', 'predicate': 'knows', 'object': 'Bob'},
                ]
            }
        ]
        result = self.tcr.restore_context_for_path(paths)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['restored_context']), 1)

if __name__ == '__main__':
    unittest.main()