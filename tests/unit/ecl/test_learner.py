import unittest
from src.ecl.learner import ExternalContinualLearner

class TestExternalContinualLearner(unittest.TestCase):
    def setUp(self):
        self.learner = ExternalContinualLearner()

    def test_update_embeddings(self):
        domain_name = "TestDomain"
        documents = [
            {"id": "doc1", "text": "This is a test document"}
        ]
        result = self.learner.update_embeddings(domain=domain_name, documents=documents)
        self.assertIn('success', result)
        self.assertIn('domain', result)
        self.assertIn('updated_count', result)

    def test_generate_embedding(self):
        document = {"id": "doc1", "text": "This is a test document"}
        embedding = self.learner._generate_embedding(document)
        self.assertIsNotNone(embedding)
        self.assertIn('document_id', embedding)
        self.assertIn('embedding_vector', embedding)

if __name__ == '__main__':
    unittest.main()