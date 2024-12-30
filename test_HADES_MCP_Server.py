import unittest
from unittest.mock import patch, MagicMock, mock_open
from HADES_MCP_Server import ConnectionManager, MCPError

class TestConnectionManager(unittest.TestCase):
    def setUp(self):
        self.db_config = {
            "url": "http://localhost:8529",
            "database": "_system",
            "username": "root",
            "password": ""
        }
        self.milvus_config = {
            "host": "localhost",
            "port": 19530,
            "username": "",
            "password": ""
        }
        self.conn_manager = ConnectionManager(self.db_config, self.milvus_config)

    @patch('HADES_MCP_Server.ArangoClient')
    def test_get_db_success(self, mock_arango_client):
        mock_client_instance = MagicMock()
        mock_db_instance = MagicMock()
        mock_arango_client.return_value = mock_client_instance
        mock_client_instance.db.return_value = mock_db_instance

        db = self.conn_manager.get_db()

        self.assertEqual(db, mock_db_instance)
        mock_arango_client.assert_called_once_with(hosts=self.db_config['url'])
        mock_client_instance.db.assert_called_once_with(
            self.db_config['database'],
            username=self.db_config['username'],
            password=self.db_config['password']
        )

    @patch('HADES_MCP_Server.ArangoClient')
    def test_get_db_failure(self, mock_arango_client):
        mock_client_instance = MagicMock()
        mock_arango_client.return_value = mock_client_instance
        mock_client_instance.db.side_effect = Exception("Connection failed")

        with self.assertRaises(MCPError) as context:
            self.conn_manager.get_db()

        self.assertEqual(context.exception.code, "DB_CONNECTION_ERROR")
        self.assertIn("Failed to connect to ArangoDB", context.exception.message)
        mock_arango_client.assert_called_once_with(hosts=self.db_config['url'])
        self.assertEqual(mock_client_instance.db.call_count, 3)

    @patch('HADES_MCP_Server.connections')
    def test_ensure_milvus_success(self, mock_connections):
        self.conn_manager.ensure_milvus()

        mock_connections.connect.assert_called_once_with(
            alias="default",
            host=self.milvus_config['host'],
            port=self.milvus_config['port'],
            user=self.milvus_config['username'],
            password=self.milvus_config['password']
        )
        self.assertTrue(self.conn_manager._milvus_connected)

    @patch('HADES_MCP_Server.connections')
    def test_ensure_milvus_failure(self, mock_connections):
        mock_connections.connect.side_effect = Exception("Connection failed")

        with self.assertRaises(MCPError) as context:
            self.conn_manager.ensure_milvus()

        self.assertEqual(context.exception.code, "MILVUS_CONNECTION_ERROR")
        self.assertIn("Failed to connect to Milvus", context.exception.message)
        mock_connections.connect.assert_called_once_with(
            alias="default",
            host=self.milvus_config['host'],
            port=self.milvus_config['port'],
            username=self.milvus_config['username'],
            password=self.milvus_config['password']
)
        self.assertFalse(self.conn_manager._milvus_connected)

    def test_close_connections(self):
        mock_client = MagicMock()
        self.conn_manager._client = mock_client
        self.conn_manager._milvus_connected = True

        self.conn_manager.close()

        mock_client.close.assert_called_once()
        connections.disconnect.assert_called_once_with("default")
        self.assertIsNone(self.conn_manager._client)
        self.assertFalse(self.conn_manager._milvus_connected)

    @patch('HADES_MCP_Server.ArangoClient')
    def test_get_db_retry_success(self, mock_arango_client):
        mock_client_instance = MagicMock()
        mock_db_instance = MagicMock()
        mock_arango_client.return_value = mock_client_instance
        mock_client_instance.db.side_effect = [Exception("Connection failed"), mock_db_instance]

        db = self.conn_manager.get_db()

        self.assertEqual(db, mock_db_instance)
        mock_arango_client.assert_called_with(hosts=self.db_config['url'])
        self.assertEqual(mock_client_instance.db.call_count, 2)

    @patch('HADES_MCP_Server.ArangoClient')
    def test_get_db_retry_failure(self, mock_arango_client):
        mock_client_instance = MagicMock()
        mock_arango_client.return_value = mock_client_instance
        mock_client_instance.db.side_effect = Exception("Connection failed")

        with self.assertRaises(MCPError) as context:
            self.conn_manager.get_db()

        self.assertEqual(context.exception.code, "DB_CONNECTION_ERROR")
        self.assertIn("Failed to connect to ArangoDB", context.exception.message)
        self.assertEqual(mock_client_instance.db.call_count, 3)

    @patch('HADES_MCP_Server.connections')
    def test_ensure_milvus_retry_success(self, mock_connections):
        mock_connections.connect.side_effect = [Exception("Connection failed"), None]

        self.conn_manager.ensure_milvus()

        mock_connections.connect.assert_called_with(
            alias="default",
            host=self.milvus_config['host'],
            port=self.milvus_config['port'],
            user=self.milvus_config['username'],
            password=self.milvus_config['password']
        )
        self.assertEqual(mock_connections.connect.call_count, 2)
        self.assertTrue(self.conn_manager._milvus_connected)

    @patch('HADES_MCP_Server.connections')
    def test_ensure_milvus_retry_failure(self, mock_connections):
        mock_connections.connect.side_effect = Exception("Connection failed")

        with self.assertRaises(MCPError) as context:
            self.conn_manager.ensure_milvus()

        self.assertEqual(context.exception.code, "MILVUS_CONNECTION_ERROR")
        self.assertIn("Failed to connect to Milvus", context.exception.message)
        mock_connections.connect.assert_called_once_with(
            alias="default",
            host=self.milvus_config['host'],
            port=self.milvus_config['port'],
            user=self.milvus_config['username'],
            password=self.milvus_config['password']
        )
        self.assertFalse(self.conn_manager._milvus_connected)

    if __name__ == '__main__':
        unittest.main()
