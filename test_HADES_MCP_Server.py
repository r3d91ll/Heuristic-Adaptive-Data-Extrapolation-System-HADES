import unittest
import os
import asyncio
from unittest.mock import patch, MagicMock
from HADES_MCP_Server import (
    DatabaseConfig,
    MilvusConfig,
    ServerConfig,
    QueryArgs,
    VectorSearchArgs,
    HybridSearchArgs,
    ConnectionManager,
    VectorDBMCPServer,
    MCPError
)

class TestDatabaseConfig(unittest.TestCase):
    def test_default_values(self):
        config = DatabaseConfig(url="http://localhost:8529", database="_system", username="root", password="")
        self.assertEqual(config.url, "http://localhost:8529")
        self.assertEqual(config.database, "_system")
        self.assertEqual(config.username, "root")
        self.assertEqual(config.password, "")

    @patch.dict(os.environ, {"ARANGO_URL": "http://test-url", "ARANGO_DB": "test-db", "ARANGO_USER": "test-user", "ARANGO_PASSWORD": "test-password"})
    def test_env_values(self):
        config = DatabaseConfig(url=os.getenv("ARANGO_URL"), database=os.getenv("ARANGO_DB"), username=os.getenv("ARANGO_USER"), password=os.getenv("ARANGO_PASSWORD"))
        self.assertEqual(config.url, os.getenv("ARANGO_URL"))
        self.assertEqual(config.database, os.getenv("ARANGO_DB"))
        self.assertEqual(config.username, os.getenv("ARANGO_USER"))
        self.assertEqual(config.password, os.getenv("ARANGO_PASSWORD"))

class TestMilvusConfig(unittest.TestCase):
    def test_default_values(self):
        config = MilvusConfig(host="localhost", port=19530, username="", password="")
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 19530)
        self.assertEqual(config.username, "")
        self.assertEqual(config.password, "")

    @patch.dict(os.environ, {"MILVUS_HOST": "test-host", "MILVUS_PORT": "12345", "MILVUS_USER": "test-user", "MILVUS_PASSWORD": "test-password"})
    def test_env_values(self):
        config = MilvusConfig(host=os.getenv("MILVUS_HOST"), port=int(os.getenv("MILVUS_PORT")), username=os.getenv("MILVUS_USER"), password=os.getenv("MILVUS_PASSWORD"))
        self.assertEqual(config.host, os.getenv("MILVUS_HOST"))
        self.assertEqual(config.port, int(os.getenv("MILVUS_PORT")))
        self.assertEqual(config.username, os.getenv("MILVUS_USER"))
        self.assertEqual(config.password, os.getenv("MILVUS_PASSWORD"))

    def test_invalid_port(self):
        with self.assertRaises(ValueError) as context:
            MilvusConfig(port=65536)
        self.assertIn("Port must be between 1 and 65535", str(context.exception))

class TestServerConfig(unittest.TestCase):
    def test_default_values(self):
        config = ServerConfig(thread_pool_size=5, max_concurrent_requests=100, request_timeout=30.0)
        self.assertEqual(config.thread_pool_size, 5)
        self.assertEqual(config.max_concurrent_requests, 100)
        self.assertEqual(config.request_timeout, 30.0)

    @patch.dict(os.environ, {"SERVER_THREAD_POOL_SIZE": "10", "SERVER_MAX_CONCURRENT_REQUESTS": "200", "SERVER_REQUEST_TIMEOUT": "60.0"})
    def test_env_values(self):
        config = ServerConfig(thread_pool_size=int(os.getenv("SERVER_THREAD_POOL_SIZE")), max_concurrent_requests=int(os.getenv("SERVER_MAX_CONCURRENT_REQUESTS")), request_timeout=float(os.getenv("SERVER_REQUEST_TIMEOUT")))
        self.assertEqual(config.thread_pool_size, int(os.getenv("SERVER_THREAD_POOL_SIZE")))
        self.assertEqual(config.max_concurrent_requests, int(os.getenv("SERVER_MAX_CONCURRENT_REQUESTS")))
        self.assertEqual(config.request_timeout, float(os.getenv("SERVER_REQUEST_TIMEOUT")))

class TestQueryArgs(unittest.TestCase):
    def test_valid_query(self):
        args = QueryArgs(query="FOR doc IN collection RETURN doc")
        self.assertEqual(args.query, "FOR doc IN collection RETURN doc")

    def test_invalid_query(self):
        with self.assertRaises(ValueError) as context:
            QueryArgs(query="")
        self.assertIn("Query cannot be empty", str(context.exception))

class TestVectorSearchArgs(unittest.TestCase):
    def test_valid_vector_search_args(self):
        args = VectorSearchArgs(collection="test_collection", vector=[1.0, 2.0, 3.0])
        self.assertEqual(args.collection, "test_collection")
        self.assertEqual(args.vector, [1.0, 2.0, 3.0])

    def test_invalid_vector_search_args(self):
        with self.assertRaises(ValueError) as context:
            VectorSearchArgs(collection="test_collection", vector=[])
        self.assertIn("Vector cannot be empty", str(context.exception))

class TestHybridSearchArgs(unittest.TestCase):
    def test_valid_hybrid_search_args(self):
        args = HybridSearchArgs(milvus_collection="milvus_test", arango_collection="arango_test", query_text="test_query")
        self.assertEqual(args.milvus_collection, "milvus_test")
        self.assertEqual(args.arango_collection, "arango_test")
        self.assertEqual(args.query_text, "test_query")

class TestConnectionManager(unittest.TestCase):
    @patch('HADES_MCP_Server.ArangoClient')
    @patch('HADES_MCP_Server.connections.connect')
    async def test_get_db(self, mock_connect, mock_arango_client):
        db_config = DatabaseConfig()
        milvus_config = MilvusConfig()
        conn_manager = ConnectionManager(db_config, milvus_config)
        
        mock_arango_client.return_value.db.return_value = "mock_db"
        result = await conn_manager.get_db()
        self.assertEqual(result, "mock_db")

    @patch('HADES_MCP_Server.connections.connect')
    async def test_ensure_milvus(self, mock_connect):
        db_config = DatabaseConfig()
        milvus_config = MilvusConfig()
        conn_manager = ConnectionManager(db_config, milvus_config)
        
        await conn_manager.ensure_milvus()
        mock_connect.assert_called_once_with(
            alias="default",
            host=milvus_config.host,
            port=milvus_config.port,
            user=milvus_config.username,
            password=milvus_config.password
        )

    @patch('HADES_MCP_Server.ArangoClient')
    @patch('HADES_MCP_Server.connections.connect')
    async def test_close(self, mock_connect, mock_arango_client):
        db_config = DatabaseConfig()
        milvus_config = MilvusConfig()
        conn_manager = ConnectionManager(db_config, milvus_config)
        
        await conn_manager.get_db()
        await conn_manager.ensure_milvus()
        conn_manager.close()
        mock_arango_client.return_value.close.assert_called_once()
        mock_connect.assert_called_once_with(
            alias="default",
            host=milvus_config.host,
            port=milvus_config.port,
            user=milvus_config.username,
            password=milvus_config.password
        )

    @patch('HADES_MCP_Server.ArangoClient')
    @patch('HADES_MCP_Server.connections.connect', side_effect=Exception("Connection failed"))
    async def test_get_db_retry(self, mock_connect, mock_arango_client):
        db_config = DatabaseConfig()
        milvus_config = MilvusConfig()
        conn_manager = ConnectionManager(db_config, milvus_config)
        
        with self.assertRaises(MCPError) as context:
            await conn_manager.get_db()
        self.assertIn("Failed to connect to ArangoDB", str(context.exception))

    @patch('HADES_MCP_Server.connections.connect', side_effect=Exception("Connection failed"))
    async def test_ensure_milvus_retry(self, mock_connect):
        db_config = DatabaseConfig()
        milvus_config = MilvusConfig()
        conn_manager = ConnectionManager(db_config, milvus_config)
        
        with self.assertRaises(MCPError) as context:
            await conn_manager.ensure_milvus()
        self.assertIn("Failed to connect to Milvus", str(context.exception))

class TestVectorDBMCPServer(unittest.TestCase):
    @patch('HADES_MCP_Server.DatabaseConfig')
    @patch('HADES_MCP_Server.MilvusConfig')
    @patch('HADES_MCP_Server.ServerConfig')
    def setUp(self, mock_server_config, mock_milvus_config, mock_db_config):
        self.db_config = mock_db_config.return_value
        self.milvus_config = mock_milvus_config.return_value
        self.server_config = mock_server_config.return_value
        
        # Ensure ServerConfig returns a valid integer for thread_pool_size
        self.server_config.thread_pool_size = 5
        self.conn_manager = ConnectionManager(self.db_config, self.milvus_config)
        self.server = VectorDBMCPServer()

    @patch('HADES_MCP_Server.ThreadPoolExecutor')
    def test_init(self, mock_thread_pool_executor):
        self.assertEqual(self.server.name, "vector-db-mcp-server")
        self.assertIsNotNone(self.server.conn_manager)
        self.assertIsNotNone(self.server._executor)
        self.assertIsNotNone(self.server.tools)
        self.assertIsNotNone(self.server.metadata)
        self.assertIsNotNone(self.server.capabilities)

    @patch('HADES_MCP_Server.ConnectionManager.get_db')
    async def test_execute_query(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.aql.execute.return_value = [{"key": "value"}]
        
        result = await self.server.execute_query("FOR doc IN collection RETURN doc")
        self.assertEqual(result, [{"key": "value"}])

    @patch('HADES_MCP_Server.ConnectionManager.get_db')
    async def test_execute_query_error(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.aql.execute.side_effect = Exception("Query failed")
        
        with self.assertRaises(MCPError) as context:
            await self.server.execute_query("FOR doc IN collection RETURN doc")
        self.assertIn("Query execution failed", str(context.exception))

    @patch('HADES_MCP_Server.ConnectionManager.ensure_milvus')
    @patch('HADES_MCP_Server.Collection.search', side_effect=Exception("Search failed"))
    @patch('HADES_MCP_Server.VectorDBMCPServer.execute_query')
    async def test_hybrid_search_vector_error(self, mock_execute_query, mock_collection_search, mock_ensure_milvus):
        args = HybridSearchArgs(
            milvus_collection="test_collection",
            arango_collection="test_arango",
            query_text="test_query",
            vector=[1.0, 2.0, 3.0],
            limit=5
        )
        
        with self.assertRaises(MCPError) as context:
            await self.server.hybrid_search(args)
        self.assertIn("Hybrid search failed", str(context.exception))

    @patch('HADES_MCP_Server.ConnectionManager.ensure_milvus')
    @patch('HADES_MCP_Server.Collection.search', return_value=[[MagicMock(id=1)]])
    @patch('HADES_MCP_Server.VectorDBMCPServer.execute_query', side_effect=Exception("Query failed"))
    async def test_hybrid_search_document_error(self, mock_execute_query, mock_collection_search, mock_ensure_milvus):
        args = HybridSearchArgs(
            milvus_collection="test_collection",
            arango_collection="test_arango",
            query_text="test_query",
            vector=[1.0, 2.0, 3.0],
            limit=5
        )
        
        with self.assertRaises(MCPError) as context:
            await self.server.hybrid_search(args)
        self.assertIn("Hybrid search failed", str(context.exception))

    @patch('HADES_MCP_Server.ConnectionManager.ensure_milvus')
    @patch('HADES_MCP_Server.Collection.search', return_value=[[MagicMock(id=1)]])
    @patch('HADES_MCP_Server.VectorDBMCPServer.execute_query', return_value=[{"key": "value"}])
    async def test_hybrid_search(self, mock_execute_query, mock_collection_search, mock_ensure_milvus):
        args = HybridSearchArgs(
            milvus_collection="test_collection",
            arango_collection="test_arango",
            query_text="test_query",
            vector=[1.0, 2.0, 3.0],
            limit=5
        )
        
        result = await self.server.hybrid_search(args)
        self.assertEqual(result, [{"key": "value"}])

    async def test_handle_list_tools(self):
        request = MagicMock()
        request.params.name = "test_tool"
        result = await self.server.handle_list_tools(request)
        self.assertIn("tools", result)

    @patch('HADES_MCP_Server.VectorDBMCPServer.execute_query')
    async def test_handle_call_tool(self, mock_execute_query):
        request = MagicMock()
        request.params.name = "execute_query"
        request.params.arguments = {"query": "FOR doc IN collection RETURN doc"}
        
        mock_execute_query.return_value = [{"key": "value"}]
        result = await self.server.handle_call_tool(request)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], [{"key": "value"}])

    @patch('HADES_MCP_Server.VectorDBMCPServer.execute_query')
    async def test_handle_call_tool_tool_not_found(self, mock_execute_query):
        request = MagicMock()
        request.params.name = "non_existent_tool"
        request.params.arguments = {"query": "FOR doc IN collection RETURN doc"}
        
        result = await self.server.handle_call_tool(request)
        self.assertFalse(result["success"])
        self.assertIn("Tool not found", str(result["error"]["message"]))

    @patch('HADES_MCP_Server.VectorDBMCPServer.execute_query')
    async def test_handle_call_tool_validation_error(self, mock_execute_query):
        request = MagicMock()
        request.params.name = "execute_query"
        request.params.arguments = {"query": ""}
        
        result = await self.server.handle_call_tool(request)
        self.assertFalse(result["success"])
        self.assertIn("Invalid arguments", str(result["error"]["message"]))

    @patch('HADES_MCP_Server.VectorDBMCPServer.execute_query')
    async def test_handle_call_tool_timeout(self, mock_execute_query):
        request = MagicMock()
        request.params.name = "execute_query"
        request.params.arguments = {"query": "FOR doc IN collection RETURN doc"}
        
        mock_execute_query.side_effect = asyncio.TimeoutError
        result = await self.server.handle_call_tool(request)
        self.assertFalse(result["success"])
        self.assertIn("Tool execution timed out", str(result["error"]["message"]))

    @patch('HADES_MCP_Server.ConnectionManager.get_db')
    @patch('HADES_MCP_Server.connections.connect')
    async def test_health_check(self, mock_connect, mock_get_db):
        result = await self.server.health_check()
        self.assertIn("status", result)
        self.assertIn("uptime", result)
        self.assertIn("connections", result)

if __name__ == "__main__":
    unittest.main()
