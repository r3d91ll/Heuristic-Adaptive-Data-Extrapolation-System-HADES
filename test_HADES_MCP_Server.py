import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import time
from datetime import datetime, UTC
from pydantic import ValidationError, BaseModel, Field
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

@pytest.fixture
def env_setup(monkeypatch):
    def _env_setup(env_vars):
        for key, value in env_vars.items():
            monkeypatch.setenv(key, str(value))
    return _env_setup

class TestDatabaseConfig:
    def test_default_values(self):
        config = DatabaseConfig()
        assert config.url == "http://localhost:8529"
        assert config.database == "_system"
        assert config.username == "root"
        assert config.password == ""
        assert config.container_name == "hades_arangodb"
        assert config.port == 8529
        assert config.root_password == "your_secure_password"
        assert config.data_volume == "hades_arango_data"
        assert config.apps_volume == "hades_arango_apps"

    def test_env_values(self, env_setup):
        env_setup({
            "url": "http://test-url",
            "database": "test-db",
            "username": "test-user",
            "password": "test-password",
            "container_name": "test-container",
            "port": "8529",
            "root_password": "test-root-password",
            "data_volume": "test-data-volume",
            "apps_volume": "test-apps-volume"
        })
        config = DatabaseConfig(_env_file=None)
        assert config.url == "http://test-url"
        assert config.database == "test-db"
        assert config.username == "test-user"
        assert config.password == "test-password"
        assert config.container_name == "test-container"
        assert config.port == 8529
        assert config.root_password == "test-root-password"
        assert config.data_volume == "test-data-volume"
        assert config.apps_volume == "test-apps-volume"

class TestMilvusConfig:
    def test_default_values(self):
        config = MilvusConfig()
        assert config.host == "localhost"
        assert config.port == 19530
        assert config.username == "root"
        assert config.password == "your_secure_password"
        assert config.container_name == "hades_milvus"
        assert config.data_volume == "hades_milvus_data"

    def test_env_values(self, env_setup):
        env_setup({
            "host": "test-host",
            "port": "19531",
            "username": "test-user",
            "password": "test-password",
            "container_name": "test-milvus",
            "data_volume": "test-milvus-data"
        })
        config = MilvusConfig(_env_file=None)
        assert config.host == "test-host"
        assert config.port == 19531
        assert config.username == "test-user"
        assert config.password == "test-password"
        assert config.container_name == "test-milvus"
        assert config.data_volume == "test-milvus-data"

    def test_invalid_port(self):
        with pytest.raises(ValueError) as exc_info:
            MilvusConfig(port=65536)
        assert "Port must be between 1 and 65535" in str(exc_info.value)

class TestServerConfig:
    def test_default_values(self):
        config = ServerConfig()
        assert config.thread_pool_size == 5
        assert config.max_concurrent_requests == 100
        assert config.request_timeout == 30.0
        assert config.etcd_container_name == "hades_etcd"
        assert config.minio_container_name == "hades_minio"
        assert config.etcd_data_volume == "hades_etcd_data"
        assert config.minio_data_volume == "hades_minio_data"
        assert config.docker_network_name == "hades_network"

    def test_env_values(self, env_setup):
        env_setup({
            "thread_pool_size": "10",
            "max_concurrent_requests": "200",
            "request_timeout": "60.0",
            "etcd_container_name": "test-etcd",
            "minio_container_name": "test-minio",
            "etcd_data_volume": "test-etcd-data",
            "minio_data_volume": "test-minio-data",
            "docker_network_name": "test-network"
        })
        config = ServerConfig(_env_file=None)
        assert config.thread_pool_size == 10
        assert config.max_concurrent_requests == 200
        assert config.request_timeout == 60.0
        assert config.etcd_container_name == "test-etcd"
        assert config.minio_container_name == "test-minio"
        assert config.etcd_data_volume == "test-etcd-data"
        assert config.minio_data_volume == "test-minio-data"
        assert config.docker_network_name == "test-network"

class TestQueryArgs:
    def test_valid_query(self):
        args = QueryArgs(query="FOR doc IN collection RETURN doc")
        assert args.query == "FOR doc IN collection RETURN doc"

    def test_invalid_query(self):
        with pytest.raises(ValueError) as exc_info:
            QueryArgs(query="")
        assert "Query string cannot be empty" in str(exc_info.value)

class TestVectorSearchArgs:
    def test_valid_vector_search_args(self):
        args = VectorSearchArgs(collection="test_collection", vector=[1.0, 2.0, 3.0])
        assert args.collection == "test_collection"
        assert args.vector == [1.0, 2.0, 3.0]

    def test_invalid_vector_search_args(self):
        with pytest.raises(ValueError) as exc_info:
            VectorSearchArgs(collection="test_collection", vector=[])
        assert "Vector cannot be empty" in str(exc_info.value)

class TestHybridSearchArgs:
    def test_valid_hybrid_search_args(self):
        args = HybridSearchArgs(
            milvus_collection="milvus_test",
            arango_collection="arango_test",
            query_text="test_query",
            vector=[1.0, 2.0, 3.0]
        )
        assert args.milvus_collection == "milvus_test"
        assert args.arango_collection == "arango_test"
        assert args.query_text == "test_query"
        assert args.vector == [1.0, 2.0, 3.0]

class TestMCPError:
    def test_mcp_error_creation(self):
        error = MCPError("TEST_ERROR", "Test message", {"detail": "test"})
        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.details == {"detail": "test"}
        assert isinstance(error.timestamp, datetime)

class TestConnectionManager:
    @pytest.fixture
    async def conn_manager(self):
        db_config = DatabaseConfig()
        milvus_config = MilvusConfig()
        return ConnectionManager(db_config, milvus_config)

    @pytest.fixture
    def mock_arango_client(self, monkeypatch):
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.db.return_value = mock_db
        
        def mock_client_constructor(*args, **kwargs):
            return mock_client
            
        monkeypatch.setattr('HADES_MCP_Server.ArangoClient', mock_client_constructor)
        return mock_client, mock_db

    async def test_ensure_milvus(self, conn_manager):
        with patch('HADES_MCP_Server.connections') as mock_connections:
            await conn_manager.ensure_milvus()
            mock_connections.connect.assert_called_once()

    async def test_get_db(self, conn_manager, mock_arango_client):
        mock_client, mock_db = mock_arango_client
        result = await conn_manager.get_db()
        assert result == mock_db
        mock_client.db.assert_called_once()

    async def test_get_db_retry_success(self, conn_manager, mock_arango_client):
        mock_client, mock_db = mock_arango_client
        mock_client.db.side_effect = [Exception("First try"), mock_db]
        result = await conn_manager.get_db()
        assert result == mock_db
        assert mock_client.db.call_count == 2

    async def test_get_db_all_retries_fail(self, conn_manager, mock_arango_client):
        mock_client, _ = mock_arango_client
        mock_client.db.side_effect = Exception("Connection failed")
        with pytest.raises(MCPError) as exc_info:
            await conn_manager.get_db()
        assert "Failed to connect to ArangoDB" in str(exc_info.value)

    async def test_ensure_milvus_retry_success(self, conn_manager):
        with patch('HADES_MCP_Server.connections') as mock_connections:
            mock_connections.connect.side_effect = [Exception("First try"), None]
            await conn_manager.ensure_milvus()
            assert mock_connections.connect.call_count == 2

    async def test_ensure_milvus_all_retries_fail(self, conn_manager):
        with patch('HADES_MCP_Server.connections') as mock_connections:
            mock_connections.connect.side_effect = Exception("Connection failed")
            with pytest.raises(MCPError) as exc_info:
                await conn_manager.ensure_milvus()
            assert "Failed to connect to Milvus" in str(exc_info.value)

    def test_close(self, conn_manager):
        mock_client = MagicMock()
        conn_manager._client = mock_client
        conn_manager._milvus_connected = True
        
        with patch('HADES_MCP_Server.connections') as mock_connections:
            conn_manager.close()
            mock_client.close.assert_called_once()
            mock_connections.disconnect.assert_called_once_with("default")
            assert conn_manager._client is None
            assert not conn_manager._milvus_connected

@pytest.mark.asyncio
class TestVectorDBMCPServer:
    @pytest.fixture
    async def server(self):
        with patch('HADES_MCP_Server.ConnectionManager') as mock_cm:
            server = VectorDBMCPServer()
            server.close = AsyncMock()
            server.conn_manager = mock_cm.return_value
            server.conn_manager.get_db = AsyncMock()
            server.start_time = time.time()
            return server

    async def test_handle_request(self, server):
        request = MagicMock()
        request_type = type(request)
        handler_mock = AsyncMock(return_value="response")
        server._handlers[request_type] = handler_mock
        result = await server.handle_request(request)
        assert result == "response"
        handler_mock.assert_called_once_with(request)

    async def test_handle_request_no_handler(self, server):
        request = MagicMock()
        with pytest.raises(MCPError) as exc_info:
            await server.handle_request(request)
        assert "REQUEST_TYPE_NOT_FOUND" in str(exc_info.value)

    async def test_close(self, server):
        await server.close()
        server.conn_manager.close.assert_called_once()

    async def test_handle_shutdown(self, server, monkeypatch):
        mock_signal_handler = MagicMock()
        monkeypatch.setattr(signal, 'signal', mock_signal_handler)
        server._handle_shutdown(15, None)
        server.close.assert_called_once()
        assert mock_signal_handler.call_count == 2

    async def test_run(self, server, monkeypatch):
        mock_transport = MagicMock()
        mock_connect = AsyncMock()
        mock_transport.connect = mock_connect
        with patch('HADES_MCP_Server.StdioServerParameters', return_value=mock_transport):
            await server.run()
            mock_connect.assert_called_once()

    async def test_execute_query(self, server):
        mock_db = MagicMock()
        mock_db.aql.execute = MagicMock(return_value=[{"key": "value"}])
        server.conn_manager.get_db.return_value = mock_db
        
        result = await server.execute_query("FOR doc IN collection RETURN doc")
        assert result == [{"key": "value"}]

    async def test_handle_call_tool(self, server):
        request = MagicMock()
        request.params.name = "execute_query"
        request.params.arguments = {"query": "FOR doc IN collection RETURN doc"}
        
        mock_db = MagicMock()
        mock_db.aql.execute = MagicMock(return_value=[{"key": "value"}])
        server.conn_manager.get_db.return_value = mock_db
        
        result = await server.handle_call_tool(request)
        assert result["success"]
        assert result["result"] == [{"key": "value"}]

    async def test_health_check(self, server):
        server.conn_manager.get_db = AsyncMock()
        server.conn_manager.ensure_milvus = AsyncMock()
        
        result = await server.health_check()
        assert result["status"] == "ok"
        assert "uptime" in result
        assert "connections" in result

    async def test_execute_query_with_bind_vars(self, server):
        mock_db = MagicMock()
        mock_db.aql.execute = MagicMock(return_value=[{"key": "value"}])
        server.conn_manager.get_db.return_value = mock_db
        
        result = await server.execute_query(
            "FOR doc IN collection FILTER doc.id == @id RETURN doc",
            {"id": "123"}
        )
        assert result == [{"key": "value"}]
        mock_db.aql.execute.assert_called_with(
            "FOR doc IN collection FILTER doc.id == @id RETURN doc",
            bind_vars={"id": "123"}
        )

    async def test_execute_query_error(self, server):
        mock_db = MagicMock()
        mock_db.aql.execute = MagicMock(side_effect=Exception("Query failed"))
        server.conn_manager.get_db.return_value = mock_db
        
        with pytest.raises(MCPError) as exc_info:
            await server.execute_query("FOR doc IN collection RETURN doc")
        assert "Query execution failed" in str(exc_info.value)

    async def test_hybrid_search_success(self, server):
        # Mock Milvus collection and connection
        mock_collection = MagicMock()
        mock_collection.search.return_value = [[MagicMock(id="doc1"), MagicMock(id="doc2")]]
        server.conn_manager.ensure_milvus = AsyncMock()
        
        with patch('pymilvus.Collection', return_value=mock_collection):
            # Mock ArangoDB query
            mock_db = MagicMock()
            mock_db.aql.execute = MagicMock(return_value=[{"id": "doc1"}, {"id": "doc2"}])
            server.conn_manager.get_db.return_value = mock_db
            
            result = await server.hybrid_search(HybridSearchArgs(
                milvus_collection="test_collection",
                arango_collection="test_docs",
                query_text="test query",
                limit=2,
                vector=[0.1, 0.2, 0.3]
            ))
            
            assert len(result) == 2
            assert result[0]["id"] == "doc1"
            assert result[1]["id"] == "doc2"

    async def test_hybrid_search_with_filters(self, server):
        # Mock Milvus collection and connection
        mock_collection = MagicMock()
        mock_collection.search.return_value = [[MagicMock(id="doc1")]]
        server.conn_manager.ensure_milvus = AsyncMock()
        
        with patch('pymilvus.Collection', return_value=mock_collection):
            # Mock ArangoDB query
            mock_db = MagicMock()
            mock_db.aql.execute = MagicMock(return_value=[{"id": "doc1"}])
            server.conn_manager.get_db.return_value = mock_db
            
            result = await server.hybrid_search(HybridSearchArgs(
                milvus_collection="test_collection",
                arango_collection="test_docs",
                query_text="test query",
                limit=1,
                filters={"category": "test"},
                vector=[0.1, 0.2, 0.3]
            ))
            
            assert len(result) == 1
            assert result[0]["id"] == "doc1"

    async def test_hybrid_search_error(self, server):
        server.conn_manager.ensure_milvus = AsyncMock()
        with patch('pymilvus.Collection', side_effect=Exception("Search failed")):
            with pytest.raises(MCPError) as exc_info:
                await server.hybrid_search(HybridSearchArgs(
                    milvus_collection="test_collection",
                    arango_collection="test_docs",
                    query_text="test query",
                    vector=[0.1, 0.2, 0.3]
                ))
            assert "Search failed" in str(exc_info.value)

    async def test_handle_list_tools_request(self, server):
        request = MagicMock()
        result = await server.handle_list_tools(request)
        assert "tools" in result
        assert isinstance(result["tools"], list)
        assert len(result["tools"]) > 0
        for tool in result["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    async def test_handle_call_tool_not_found(self, server):
        request = MagicMock()
        request.params.name = "nonexistent_tool"
        result = await server.handle_call_tool(request)
        assert not result["success"]
        assert result["error"]["code"] == "TOOL_NOT_FOUND"

    async def test_handle_call_tool_validation_error(self, server):
        request = MagicMock()
        request.params.name = "execute_query"
        request.params.arguments = {}  # Missing required 'query' parameter

        # Create a Pydantic model for validation
        class QueryModel(BaseModel):
            query: str = Field(..., description="Query string")

        server.tools = {
            "execute_query": {
                "handler": AsyncMock(),
                "schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                },
                "pydantic_model": QueryModel
            }
        }
        
        result = await server.handle_call_tool(request)
        assert not result["success"]
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "Field required" in str(result["error"]["details"])

    async def test_handle_call_tool_timeout(self, server):
        request = MagicMock()
        request.params.name = "execute_query"
        request.params.arguments = {"query": "FOR doc IN collection RETURN doc"}
        
        # Make execute_query hang
        async def hang(*args, **kwargs):
            await asyncio.sleep(2)
            
        server.tools = {
            "execute_query": {
                "handler": hang,
                "schema": {"type": "object", "properties": {"query": {"type": "string"}}}
            }
        }
        server.server_config.request_timeout = 0.1
        
        result = await server.handle_call_tool(request)
        assert not result["success"]
        assert "timed out" in result["error"]["message"].lower()

    async def test_health_check_all_healthy(self, server):
        server.conn_manager.get_db = AsyncMock()
        server.conn_manager.ensure_milvus = AsyncMock()
        
        result = await server.health_check()
        assert result["status"] == "ok"
        assert result["connections"]["arango"]
        assert result["connections"]["milvus"]

    async def test_health_check_degraded_arango(self, server):
        server.conn_manager.get_db = AsyncMock(side_effect=Exception("DB Error"))
        server.conn_manager.ensure_milvus = AsyncMock()
        
        result = await server.health_check()
        assert result["status"] == "degraded"
        assert not result["connections"]["arango"]
        assert result["connections"]["milvus"]
        assert "DB Error" in result["errors"]["arango"]

    async def test_health_check_degraded_milvus(self, server):
        server.conn_manager.get_db = AsyncMock()
        server.conn_manager.ensure_milvus = AsyncMock(side_effect=Exception("Milvus Error"))
        
        result = await server.health_check()
        assert result["status"] == "degraded"
        assert result["connections"]["arango"]
        assert not result["connections"]["milvus"]
        assert "Milvus Error" in result["errors"]["milvus"]

    async def test_annotation_to_json_schema(self, server):
        schema = server._annotation_to_json_schema(str)
        assert schema == {"type": "string"}

        schema = server._annotation_to_json_schema(int)
        assert schema == {"type": "number", "multipleOf": 1}

        schema = server._annotation_to_json_schema(float)
        assert schema == {"type": "number"}

        schema = server._annotation_to_json_schema(bool)
        assert schema == {"type": "boolean"}

        schema = server._annotation_to_json_schema(List[float])
        assert schema == {
            "type": "array",
            "items": {"type": "number"}
        }

        schema = server._annotation_to_json_schema(Dict[str, Any])
        assert schema == {
            "type": "object",
            "additionalProperties": True
        }

    async def test_get_tool_schema(self, server):
        class TestTool:
            @mcp_tool("Test tool description")
            async def test_method(self, arg1: str, arg2: int = 42) -> None:
                pass

        schema = server._get_tool_schema(TestTool.test_method)
        assert schema == {
            "type": "object",
            "properties": {
                "arg1": {"type": "string"},
                "arg2": {"type": "number", "multipleOf": 1}
            },
            "required": ["arg1"]
        }

    async def test_register_tools(self, server):
        class TestTool:
            @mcp_tool("Test tool description")
            async def test_method(self, arg1: str, arg2: int = 42) -> None:
                pass

        with patch.object(server, 'tools', {}), \
             patch.object(server, '_tool_schemas_cache', {}):
            server._register_tools()
            assert "test_method" in server.tools
            assert server.tools["test_method"]["description"] == "Test tool description"
            assert server.tools["test_method"]["handler"] is TestTool.test_method

if __name__ == "__main__":
    pytest.main()
