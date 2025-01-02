import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pydantic import ValidationError
from typing import Dict, Any, List, Optional, Union
from HADES_MCP_Server import (
    DatabaseConfig,
    MilvusConfig,
    ServerConfig,
    QueryArgs,
    VectorSearchArgs,
    HybridSearchArgs,
    MCPError,
    ConnectionManager,
    VectorDBMCPServer,
    CallToolRequest,
    ListToolsRequest
)
import time
import asyncio
import signal
import sys
import os
import concurrent.futures
import pytest_asyncio
import async_timeout

# Add before the tests
TEST_TIMEOUT = 5  # Global test timeout in seconds
OPERATION_TIMEOUT = 2  # Individual operation timeout

# Import the module under test
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import HADES_MCP_Server
from HADES_MCP_Server import VectorDBMCPServer

@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = VectorDBMCPServer()
    server.llm_service_url = "http://localhost:1234"
    return server

@pytest.mark.asyncio
async def test_enrich_context_success(mock_server):
    """Test enrich_context method success."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"enriched": "data"})
    
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await mock_server.enrich_context("test context")
        assert result == {"enriched": "data"}
        mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_generate_response_success(mock_server):
    """Test generate_response method success."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"generated": "response"})
    
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await mock_server.generate_response("test prompt")
        assert result == {"generated": "response"}
        mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_import_error_handling():
    """Test import error handling."""
    mock_transport = MagicMock()
    mock_transport.connect = MagicMock()
    mock_server = AsyncMock()
    mock_server.close = AsyncMock()
    
    with patch.dict('sys.modules', {'aiohttp': None}):
        with patch('HADES_MCP_Server.VectorDBMCPServer', return_value=mock_server):
            with patch('HADES_MCP_Server.StdioServerParameters', return_value=mock_transport):
                with patch('sys.exit', side_effect=SystemExit):
                    with pytest.raises(SystemExit):
                        import HADES_MCP_Server
                        await HADES_MCP_Server.main()

@pytest.mark.asyncio
async def test_main_success():
    """Test main function success."""
    mock_server = AsyncMock()
    mock_server.run = AsyncMock()
    mock_server.close = AsyncMock()
    
    with patch('HADES_MCP_Server.VectorDBMCPServer', return_value=mock_server):
        with patch('sys.exit', side_effect=SystemExit):
            await HADES_MCP_Server.main()
    
    mock_server.run.assert_called_once()
    mock_server.close.assert_called_once()

@pytest.mark.asyncio
async def test_main_error():
    """Test main function with error."""
    mock_server = AsyncMock()
    mock_server.run = AsyncMock(side_effect=Exception("Run failed"))
    mock_server.close = AsyncMock()
    
    with patch('HADES_MCP_Server.VectorDBMCPServer', return_value=mock_server):
        with patch('sys.exit', side_effect=SystemExit):
            with pytest.raises(SystemExit):
                await HADES_MCP_Server.main()
    
    mock_server.run.assert_called_once()
    mock_server.close.assert_called_once()

@pytest.mark.asyncio
async def test_connect_error():
    """Test connection error handling."""
    server = VectorDBMCPServer()
    mock_transport = MagicMock()
    mock_transport.connect = MagicMock(side_effect=Exception("Connection failed"))
    
    with patch('HADES_MCP_Server.logger') as mock_logger:
        with pytest.raises(SystemExit):
            server.connect(mock_transport)
            
    mock_logger.error.assert_called_once_with(
        "Failed to connect: Connection failed",
        exc_info=True
    )

@pytest.mark.asyncio
async def test_main_entry_point():
    """Test the main entry point."""
    mock_server = AsyncMock()
    mock_server.run = AsyncMock()
    mock_server.close = AsyncMock()
    
    with patch('HADES_MCP_Server.VectorDBMCPServer', return_value=mock_server):
        await HADES_MCP_Server.main()
    
    mock_server.run.assert_called_once()
    mock_server.close.assert_called_once()

@pytest.mark.asyncio
async def test_main_entry_point_error():
    """Test the main entry point with error."""
    mock_server = AsyncMock()
    mock_server.run = AsyncMock(side_effect=Exception("Run failed"))
    mock_server.close = AsyncMock()
    
    with patch('HADES_MCP_Server.VectorDBMCPServer', return_value=mock_server):
        with patch('sys.exit', side_effect=SystemExit):
            with pytest.raises(SystemExit):
                await HADES_MCP_Server.main()
    
    mock_server.run.assert_called_once()
    mock_server.close.assert_called_once()

@pytest.mark.asyncio
async def test_import_error_handling_detailed():
    """Test detailed import error handling."""
    mock_transport = MagicMock()
    mock_transport.connect = MagicMock()
    mock_server = AsyncMock()
    mock_server.close = AsyncMock()
    
    with patch.dict('sys.modules', {'aiohttp': None}):
        with patch('HADES_MCP_Server.VectorDBMCPServer', return_value=mock_server):
            with patch('HADES_MCP_Server.StdioServerParameters', return_value=mock_transport):
                with patch('sys.exit', side_effect=SystemExit) as mock_exit:
                    with pytest.raises(SystemExit):
                        import HADES_MCP_Server
                        await HADES_MCP_Server.main()
                    
                    mock_exit.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_server_health_check(mock_server):
    """Test server health check."""
    mock_server.start_time = 0
    mock_server.conn_manager.get_db = AsyncMock()
    mock_server.conn_manager.ensure_milvus = AsyncMock()
    
    status = await mock_server.health_check()
    
    assert status["status"] == "ok"
    assert "uptime" in status
    assert status["connections"]["arango"] is True
    assert status["connections"]["milvus"] is True

@pytest.mark.asyncio
async def test_server_health_check_degraded(mock_server):
    """Test server health check with degraded services."""
    mock_server.start_time = 0
    mock_server.conn_manager.get_db = AsyncMock(side_effect=Exception("DB Error"))
    mock_server.conn_manager.ensure_milvus = AsyncMock(side_effect=Exception("Milvus Error"))
    
    status = await mock_server.health_check()
    
    assert status["status"] == "degraded"
    assert "uptime" in status
    assert status["connections"]["arango"] is False
    assert status["connections"]["milvus"] is False
    assert "errors" in status
    assert "arango" in status["errors"]
    assert "milvus" in status["errors"]

# Test DatabaseConfig
def test_database_config_defaults():
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

def test_database_config_validation():
    with pytest.raises(ValidationError):
        DatabaseConfig(url="invalid_url")  # Invalid URL to trigger validation error

# Test MilvusConfig
def test_milvus_config_defaults():
    config = MilvusConfig()
    assert config.host == "localhost"
    assert config.port == 19530
    assert config.username == "root"
    assert config.password == "your_secure_password"
    assert config.container_name == "hades_milvus"
    assert config.data_volume == "hades_milvus_data"

def test_milvus_config_port_validation():
    with pytest.raises(ValidationError):
        MilvusConfig(port=65536)  # Invalid port number

# Test ServerConfig
def test_server_config_defaults():
    config = ServerConfig()
    assert config.thread_pool_size == 5
    assert config.max_concurrent_requests == 100
    assert config.request_timeout == 30.0
    assert config.etcd_container_name == "hades_etcd"
    assert config.minio_container_name == "hades_minio"
    assert config.etcd_data_volume == "hades_etcd_data"
    assert config.minio_data_volume == "hades_minio_data"
    assert config.docker_network_name == "hades_network"

def test_server_config_validation():
    with pytest.raises(ValidationError):
        ServerConfig(thread_pool_size=-1)  # Invalid thread pool size

def test_server_config_validation_max_concurrent():
    with pytest.raises(ValidationError):
        ServerConfig(max_concurrent_requests=-1)

def test_server_config_validation_timeout():
    with pytest.raises(ValidationError):
        ServerConfig(request_timeout=-1.0)

# Test QueryArgs
def test_query_args_valid():
    args = QueryArgs(query="FOR doc IN collection RETURN doc")
    assert args.query == "FOR doc IN collection RETURN doc"
    assert args.bind_vars is None

def test_query_args_invalid_empty():
    with pytest.raises(ValidationError):
        QueryArgs(query="")

def test_query_args_invalid_whitespace():
    with pytest.raises(ValidationError):
        QueryArgs(query="   ")

# Test VectorSearchArgs
def test_vector_search_args_valid():
    args = VectorSearchArgs(collection="test_collection", vector=[0.1, 0.2, 0.3])
    assert args.collection == "test_collection"
    assert args.vector == [0.1, 0.2, 0.3]
    assert args.limit == 5
    assert args.filters is None

def test_vector_search_args_invalid_empty_vector():
    with pytest.raises(ValidationError):
        VectorSearchArgs(collection="test_collection", vector=[])

# Test HybridSearchArgs
def test_hybrid_search_args_valid():
    args = HybridSearchArgs(
        milvus_collection="test_milvus",
        arango_collection="test_arango",
        query_text="search text",
        vector=[0.1, 0.2, 0.3]
    )
    assert args.milvus_collection == "test_milvus"
    assert args.arango_collection == "test_arango"
    assert args.query_text == "search text"
    assert args.vector == [0.1, 0.2, 0.3]
    assert args.limit == 5
    assert args.filters is None

def test_hybrid_search_args_invalid_empty_vector():
    with pytest.raises(ValidationError):
        HybridSearchArgs(
            milvus_collection="test_milvus",
            arango_collection="test_arango",
            query_text="search text",
            vector=[],  # Invalid empty vector to trigger validation error
            limit=5
        )

# Test ConnectionManager
@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_get_db(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)

    # Mock ArangoDB client and database
    mock_db = MagicMock()
    mock_client.return_value.db.return_value = mock_db
    
    db = await conn_manager.get_db()
    assert db is mock_db

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_get_db_retry(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)

    # Mock ArangoDB client and database with retry logic
    mock_db = MagicMock()
    mock_client.return_value.db.side_effect = [Exception("Connection failed"), mock_db]
    
    db = await conn_manager.get_db()
    assert db is mock_db

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_get_db_failure(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)

    # Mock ArangoDB client and database with failure
    mock_client.return_value.db.side_effect = Exception("Connection failed")

    with pytest.raises(MCPError) as excinfo:
        await conn_manager.get_db()
    assert excinfo.value.code == "DB_CONNECTION_ERROR"

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections')  # Patch the entire connections module
async def test_connection_manager_ensure_milvus(mock_connections, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)

    # Mock Milvus connection
    await conn_manager.ensure_milvus()
    assert conn_manager._milvus_connected is True

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections')  # Patch the entire connections module
async def test_connection_manager_ensure_milvus_retry(mock_connections, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)

    # Mock Milvus connection with retry logic
    mock_client.side_effect = [Exception("Connection failed"), None]
    await conn_manager.ensure_milvus()
    assert conn_manager._milvus_connected is True

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections')  # Patch the entire connections module
async def test_connection_manager_ensure_milvus_retry_failure(mock_connections, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)
    conn_manager.retry_delay = 0.1
    conn_manager.max_retries = 2

    # Mock the connections.connect to fail immediately
    mock_connections.connect.side_effect = Exception("Connection failed")

    try:
        async with async_timeout.timeout(OPERATION_TIMEOUT):
            with pytest.raises(MCPError) as excinfo:
                await conn_manager.ensure_milvus()
            assert excinfo.value.code == "MILVUS_CONNECTION_ERROR"
            assert not conn_manager._milvus_connected
    except asyncio.TimeoutError:
        pytest.fail(f"Operation timed out after {OPERATION_TIMEOUT} seconds")

# Test VectorDBMCPServer
@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
def test_vector_db_mcp_server_init(mock_executor, mock_conn_manager):
    # Create mock instances
    mock_conn = MagicMock(spec=ConnectionManager)
    mock_conn_manager.return_value = mock_conn
    
    # Create a clean server instance without any tools
    server = VectorDBMCPServer()
    server.tools = {}  # Initialize tools dictionary
    
    assert server.name == "vector-db-mcp-server"
    assert isinstance(server.server_config, ServerConfig)
    assert isinstance(server.db_config, DatabaseConfig)
    assert isinstance(server.milvus_config, MilvusConfig)
    assert server.conn_manager is mock_conn
    assert isinstance(server._executor, MagicMock)
    assert server.tools == {}

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_call_tool_validation_error(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server.tools = {}  # Initialize tools dictionary
    
    # Mock tool registration with validation
    async def validate_and_execute(args):
        if not args.get("query"):
            raise MCPError(
                code="VALIDATION_ERROR",
                message="Empty query",
                details={"field": "query", "error": "Field required"}
            )
        return [{"key": "value"}]
    
    server.tools = {
        "execute_query": {
            "handler": validate_and_execute,
            "description": "Test tool",
            "schema": {}
        }
    }
    
    request_mock = CallToolRequest(
        method="tools/call",
        params={"name": "execute_query", "arguments": {"query": ""}}
    )
    
    response = await server.handle_call_tool(request_mock)
    assert response["success"] is False
    assert response["error"]["code"] == "VALIDATION_ERROR"

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_call_tool(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    
    # Mock tool registration with timeout
    async def mock_tool(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate some work
        return [{"key": "value"}]
    
    server.tools = {
        "execute_query": {
            "handler": mock_tool,
            "description": "Test tool",
            "schema": {}
        }
    }
    
    request_mock = CallToolRequest(
        method="tools/call",
        params={"name": "execute_query", "arguments": {"query": "FOR doc IN collection RETURN doc"}}
    )
    
    try:
        async with async_timeout.timeout(OPERATION_TIMEOUT):
            response = await server.handle_call_tool(request_mock)
            assert response["success"] is True
            assert response["result"] == [{"key": "value"}]
    except asyncio.TimeoutError:
        pytest.fail(f"Operation timed out after {OPERATION_TIMEOUT} seconds")

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_execute_query(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    query_args = QueryArgs(query="FOR doc IN collection RETURN doc")

    # Mock connection manager and database
    mock_db = MagicMock()
    mock_db.aql.execute.return_value = [{"key": "value"}]
    server.conn_manager.get_db = AsyncMock(return_value=mock_db)

    result = await server.execute_query(query_args.query, query_args.bind_vars)
    assert result == [{"key": "value"}]
    mock_db.aql.execute.assert_called_once_with(query_args.query, bind_vars={})

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_execute_query_error(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    query_args = QueryArgs(query="FOR doc IN collection RETURN doc")

    # Mock connection manager and database with error
    mock_db = MagicMock()
    mock_db.aql.execute.side_effect = Exception("Query failed")
    server.conn_manager.get_db = AsyncMock(return_value=mock_db)

    with pytest.raises(MCPError) as excinfo:
        await server.execute_query(query_args.query, query_args.bind_vars)
    assert excinfo.value.code == "QUERY_ERROR"

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_hybrid_search(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server.tools = {}  # Initialize tools dictionary
    
    search_args = HybridSearchArgs(
        milvus_collection="test_milvus",
        arango_collection="test_arango",
        query_text="search text",
        vector=[0.1, 0.2, 0.3]
    )

    # Mock connection manager and database with proper document structure
    mock_db = MagicMock()
    mock_db.aql.execute.return_value = [{"_key": "1", "key": "value"}]  # Added _key field
    server.conn_manager.get_db = AsyncMock(return_value=mock_db)
    server.conn_manager.ensure_milvus = AsyncMock()

    # Mock Milvus collection search
    mock_collection = MagicMock()
    mock_hit = MagicMock()
    mock_hit.id = 1
    mock_hit.distance = 0.5
    mock_collection.search.return_value = [[mock_hit]]

    try:
        async with async_timeout.timeout(OPERATION_TIMEOUT):
            with patch('pymilvus.Collection', return_value=mock_collection):
                result = await server.hybrid_search(search_args)
                assert len(result) == 1
                assert result[0]["id"] == "1"
                assert result[0]["score"] == 0.5
    except asyncio.TimeoutError:
        pytest.fail(f"Operation timed out after {OPERATION_TIMEOUT} seconds")

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_hybrid_search_error(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    search_args = HybridSearchArgs(
        milvus_collection="test_milvus",
        arango_collection="test_arango",
        query_text="search text",
        vector=[0.1, 0.2, 0.3]
    )

    # Mock Milvus connection with error
    server.conn_manager.ensure_milvus = AsyncMock(side_effect=Exception("Milvus failed"))

    with pytest.raises(MCPError) as excinfo:
        await server.hybrid_search(search_args)
    assert excinfo.value.code == "HYBRID_SEARCH_ERROR"

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
def test_vector_db_mcp_server_close(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server.close()
    server.conn_manager.close.assert_called_once()
    server._executor.shutdown.assert_called_once_with(wait=True)

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
def test_vector_db_mcp_server_handle_shutdown(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server.close = MagicMock()

    with patch.object(sys, 'exit') as mock_exit:
        server._handle_shutdown(signal.SIGINT, None)
        server.close.assert_called_once()
        mock_exit.assert_called_once_with(0)

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
def test_vector_db_mcp_server_handle_shutdown_sigterm(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server.close = MagicMock()

    with patch.object(sys, 'exit') as mock_exit:
        server._handle_shutdown(signal.SIGTERM, None)
        server.close.assert_called_once()
        mock_exit.assert_called_once_with(0)
