import unittest
from src.core.security import Security

class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.security = Security()

    def test_authenticate_valid_credentials(self):
        result = self.security.authenticate("admin", "password")
        self.assertTrue(result['success'])
        self.assertIn('token', result)

    def test_authenticate_invalid_credentials(self):
        result = self.security.authenticate("invalid_user", "wrong_password")
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_authorize_valid_token(self):
        token = self.security.authenticate("admin", "password")["token"]
        result = self.security.authorize(token, "some_action")
        self.assertTrue(result['success'])
        self.assertTrue(result['authorized'])

    def test_authorize_invalid_token(self):
        invalid_token = "invalid.token.string"
        result = self.security.authorize(invalid_token, "some_action")
        self.assertFalse(result['success'])
        self.assertIn('error', result)

if __name__ == '__main__':
    unittest.main()